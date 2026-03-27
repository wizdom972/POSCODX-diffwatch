"""
코드 변경 이력 메모리 도구 — 분석된 코드 변경 사항을 저장하고 조회합니다.

저장 방식:
  1. rag/documents/code_changes_log.md — 마크다운 형식으로 누적 저장 (재시작 후 RAG에 자동 반영)
  2. rag/changes_index.json           — 빠른 조회를 위한 JSON 인덱스
  3. InMemoryVectorStore              — 현재 세션에서 즉시 retrieve 가능
"""

import json
from datetime import datetime
from pathlib import Path

from langchain_core.documents import Document
from langchain_core.tools import tool

CHANGES_LOG_PATH = Path(__file__).parent.parent / "rag" / "documents" / "code_changes_log.md"
CHANGES_INDEX_PATH = Path(__file__).parent.parent / "rag" / "changes_index.json"


def _load_index() -> list[dict]:
    if CHANGES_INDEX_PATH.exists():
        with open(CHANGES_INDEX_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_index(changes: list[dict]) -> None:
    with open(CHANGES_INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(changes, f, ensure_ascii=False, indent=2)


@tool
def save_change_analysis(
    commit_hash: str,
    summary: str,
    impact_level: str,
    affected_files: list,
    stakeholders: list,
    details: str = "",
) -> str:
    """코드 변경 분석 결과를 저장합니다.
    저장된 내용은 이후 retrieve 도구로 검색하거나 list_change_analyses로 조회할 수 있습니다.

    Args:
        commit_hash: 커밋 해시
        summary: 변경 요약 (한 문장)
        impact_level: 영향도 수준 ("높음", "중간", "낮음")
        affected_files: 영향받는 파일 목록
        stakeholders: 알림 받은 담당자 목록
        details: 상세 분석 내용 (선택)
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    short_hash = commit_hash[:8]

    # 1. 마크다운 파일에 누적 저장
    md_entry = (
        f"\n## [{short_hash}] {summary}\n"
        f"- **날짜:** {now}\n"
        f"- **커밋:** `{commit_hash}`\n"
        f"- **영향도:** {impact_level}\n"
        f"- **변경 파일:** {', '.join(affected_files)}\n"
        f"- **담당자:** {', '.join(stakeholders)}\n"
    )
    if details:
        md_entry += f"\n{details}\n"

    with open(CHANGES_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(md_entry)

    # 2. JSON 인덱스에 저장
    changes = _load_index()
    changes.append({
        "commit_hash": commit_hash,
        "short_hash": short_hash,
        "summary": summary,
        "impact_level": impact_level,
        "affected_files": affected_files,
        "stakeholders": stakeholders,
        "details": details,
        "saved_at": now,
    })
    _save_index(changes)

    # 3. 현재 세션 RAG 벡터 스토어에 즉시 반영
    try:
        from rag.retriever import add_documents_to_store

        doc_text = (
            f"커밋 {short_hash}: {summary}\n"
            f"날짜: {now}\n"
            f"영향도: {impact_level}\n"
            f"변경 파일: {', '.join(affected_files)}\n"
            f"담당자: {', '.join(stakeholders)}\n"
        )
        if details:
            doc_text += f"\n분석 상세:\n{details}"

        add_documents_to_store([
            Document(
                page_content=doc_text,
                metadata={"source": f"code_change/{short_hash}", "type": "code_change"},
            )
        ])
    except Exception:
        pass  # RAG 추가 실패해도 파일 저장은 성공으로 처리

    return (
        f"변경 분석 저장 완료!\n"
        f"커밋: {short_hash} | 영향도: {impact_level}\n"
        f"저장 위치: code_changes_log.md, changes_index.json\n"
        f"현재 세션 RAG에도 반영되었습니다."
    )


@tool
def list_change_analyses(limit: int = 10) -> str:
    """저장된 코드 변경 분석 이력을 최신순으로 조회합니다.

    Args:
        limit: 조회할 최대 개수 (기본값: 10)
    """
    changes = _load_index()
    if not changes:
        return "저장된 변경 분석 이력이 없습니다."

    recent = list(reversed(changes[-limit:]))
    lines = [f"총 {len(changes)}건의 변경 분석 이력 (최근 {len(recent)}건 표시):"]
    for c in recent:
        files_preview = ", ".join(c["affected_files"][:3])
        if len(c["affected_files"]) > 3:
            files_preview += f" 외 {len(c['affected_files']) - 3}개"
        lines.append(
            f"\n[{c['short_hash']}] {c['saved_at']} | 영향도: {c['impact_level']}\n"
            f"  요약: {c['summary']}\n"
            f"  파일: {files_preview}"
        )
    return "\n".join(lines)
