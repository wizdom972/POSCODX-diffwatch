"""
GitHub Webhook 수신 서버

GitHub push 이벤트를 받아 자동으로 코드 영향도 분석을 실행합니다.

실행 방법:
    uv run fastapi dev webhook_server.py --port 8001
"""

import hashlib
import hmac
import os
import asyncio

from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException

load_dotenv(override=True)

app = FastAPI()

WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")


def verify_signature(payload: bytes, signature: str) -> bool:
    """GitHub 요청 서명을 검증합니다."""
    if not WEBHOOK_SECRET:
        return True  # Secret 미설정 시 검증 생략 (개발 환경)
    expected = "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


async def run_analysis(commit_hash: str, commit_message: str, author: str):
    """에이전트를 호출해 커밋 영향도를 분석합니다."""
    from agent import create_base_agent

    print(f"\n[Webhook] 분석 시작: {commit_hash[:8]} — {commit_message}")

    agent = await create_base_agent()
    prompt = (
        f"다음 커밋의 영향도를 분석하고 담당자에게 알림을 보내줘.\n"
        f"커밋 해시: {commit_hash}\n"
        f"커밋 메시지: {commit_message}\n"
        f"작성자: {author}"
    )
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": prompt}]},
        config={"configurable": {"thread_id": commit_hash}},
    )
    print(f"[Webhook] 분석 완료: {commit_hash[:8]}")
    return result


@app.get("/")
async def health():
    return {"status": "ok", "message": "Webhook 서버 정상 동작 중"}


@app.post("/webhook")
async def handle_webhook(request: Request):
    payload = await request.body()

    # 서명 검증
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not verify_signature(payload, signature):
        raise HTTPException(status_code=403, detail="서명 검증 실패")

    # push 이벤트만 처리
    event = request.headers.get("X-GitHub-Event", "")
    if event != "push":
        print(f"[Webhook] 무시된 이벤트: {event}")
        return {"status": "ignored", "event": event}

    data = await request.json()
    head_commit = data.get("head_commit") or {}
    commit_hash = head_commit.get("id", "")
    commit_message = head_commit.get("message", "")
    author = head_commit.get("author", {}).get("name", "unknown")

    if not commit_hash:
        return {"status": "no commit"}

    print(f"[Webhook] Push 감지: {commit_hash[:8]} by {author} — {commit_message}")

    # 분석은 백그라운드에서 실행 (GitHub에 즉시 200 응답 반환)
    asyncio.create_task(run_analysis(commit_hash, commit_message, author))

    return {"status": "ok", "commit": commit_hash[:8]}
