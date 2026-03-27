"""
GitHub Webhook 수신 서버 + 관리자 대시보드

실행 방법:
    uv run fastapi dev webhook_server.py --port 8001

접속:
    대시보드 → http://localhost:8001
"""

import asyncio
import hashlib
import hmac
import json
import os
import re
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

load_dotenv(override=True)

BASE_DIR = Path(__file__).parent
CHANGES_INDEX = BASE_DIR / "rag" / "changes_index.json"
NOTIFICATIONS_LOG = BASE_DIR / "notifications_log.md"
FRONTEND_DIR = BASE_DIR / "frontend"

WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")

app = FastAPI(title="diffwatch")
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


# ─── 유틸 ──────────────────────────────────────────────────────

def verify_signature(payload: bytes, signature: str) -> bool:
    if not WEBHOOK_SECRET:
        return True
    expected = "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


async def run_analysis(commit_hash: str, commit_message: str, author: str):
    from agent import create_base_agent
    print(f"\n[Webhook] 분석 시작: {commit_hash[:8]} — {commit_message}")
    agent = await create_base_agent()
    prompt = (
        f"다음 커밋의 영향도를 분석하고 담당자에게 알림을 보내줘.\n"
        f"커밋 해시: {commit_hash}\n"
        f"커밋 메시지: {commit_message}\n"
        f"작성자: {author}"
    )
    await agent.ainvoke(
        {"messages": [{"role": "user", "content": prompt}]},
        config={"configurable": {"thread_id": commit_hash}},
    )
    print(f"[Webhook] 분석 완료: {commit_hash[:8]}")


# ─── 페이지 ────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")


# ─── API: 통계 / 커밋 / 알림 ───────────────────────────────────

@app.get("/api/stats")
async def get_stats():
    changes = json.loads(CHANGES_INDEX.read_text(encoding="utf-8")) if CHANGES_INDEX.exists() else []
    notifs = await get_notifications()
    return {
        "total_commits": len(changes),
        "high_impact": sum(1 for c in changes if c.get("impact_level") == "높음"),
        "mid_impact": sum(1 for c in changes if c.get("impact_level") == "중간"),
        "low_impact": sum(1 for c in changes if c.get("impact_level") == "낮음"),
        "total_notifications": len(notifs),
    }


@app.get("/api/changes")
async def get_changes():
    if not CHANGES_INDEX.exists():
        return []
    return list(reversed(json.loads(CHANGES_INDEX.read_text(encoding="utf-8"))))


@app.get("/api/notifications")
async def get_notifications():
    if not NOTIFICATIONS_LOG.exists():
        return []
    text = NOTIFICATIONS_LOG.read_text(encoding="utf-8")
    results = []
    for block in [b.strip() for b in text.split("---") if b.strip()]:
        if "전송 시각" not in block:
            continue
        item = {}
        for line in block.splitlines():
            line = line.strip()
            if line.startswith("**전송 시각:**"):
                item["sent_at"] = line.replace("**전송 시각:**", "").strip()
            elif line.startswith("**수신자:**"):
                item["recipients"] = line.replace("**수신자:**", "").strip()
            elif line.startswith("**제목:**"):
                item["subject"] = line.replace("**제목:**", "").strip()
        if item:
            match = re.search(r"\*\*제목:\*\*[^\n]*\n([\s\S]+)", block)
            item["body"] = match.group(1).strip() if match else ""
            results.append(item)
    return list(reversed(results))


# ─── API: 챗봇 ─────────────────────────────────────────────────

@app.post("/api/chat")
async def chat(request: Request):
    """에이전트와 대화합니다. SSE 스트림으로 응답을 반환합니다."""
    body = await request.json()
    message = body.get("message", "").strip()
    session_id = body.get("session_id", str(uuid.uuid4()))

    if not message:
        raise HTTPException(status_code=400, detail="메시지를 입력하세요.")

    async def stream():
        from agent import create_base_agent
        agent = await create_base_agent()

        async for event in agent.astream_events(
            {"messages": [{"role": "user", "content": message}]},
            config={"configurable": {"thread_id": f"chat-{session_id}"}},
            version="v2",
        ):
            kind = event.get("event")
            # AI 메시지 토큰만 스트리밍
            if kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    token = chunk.content
                    yield f"data: {json.dumps({'token': token})}\n\n"

        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


# ─── Webhook ───────────────────────────────────────────────────

@app.post("/webhook")
async def handle_webhook(request: Request):
    payload = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not verify_signature(payload, signature):
        raise HTTPException(status_code=403, detail="서명 검증 실패")

    event = request.headers.get("X-GitHub-Event", "")
    if event != "push":
        return {"status": "ignored", "event": event}

    data = await request.json()
    head_commit = data.get("head_commit") or {}
    commit_hash = head_commit.get("id", "")
    commit_message = head_commit.get("message", "")
    author = head_commit.get("author", {}).get("name", "unknown")

    if not commit_hash:
        return {"status": "no commit"}

    print(f"[Webhook] Push 감지: {commit_hash[:8]} by {author} — {commit_message}")
    asyncio.create_task(run_analysis(commit_hash, commit_message, author))
    return {"status": "ok", "commit": commit_hash[:8]}
