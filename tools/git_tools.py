"""
Git 도구 — git diff, commit 정보를 가져오는 도구들

이 파일은 tools/__init__.py에 의해 자동 수집됩니다.
"""

import os
import subprocess
from langchain_core.tools import tool

# .env의 TARGET_REPO_PATH가 있으면 해당 저장소를 대상으로 하고,
# 없으면 앱 실행 위치(현재 디렉토리)의 저장소를 사용합니다.
_REPO_PATH = os.getenv("TARGET_REPO_PATH") or None


def _run_git(args: list[str]) -> str:
    """git 명령어를 실행하고 결과를 반환합니다."""
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=_REPO_PATH,  # None이면 현재 디렉토리 사용
        )
        if result.returncode != 0:
            return f"[오류] {result.stderr.strip()}"
        return result.stdout.strip()
    except FileNotFoundError:
        return "[오류] git이 설치되어 있지 않습니다."


@tool
def get_recent_commits(count: int = 5) -> str:
    """최근 git 커밋 목록을 가져옵니다.

    Args:
        count: 가져올 커밋 수 (기본값: 5)
    """
    output = _run_git([
        "log", f"-{count}",
        "--pretty=format:%H|%an|%ae|%ad|%s",
        "--date=format:%Y-%m-%d %H:%M:%S",
    ])
    if output.startswith("[오류]"):
        return output

    lines = []
    for line in output.split("\n"):
        if not line.strip():
            continue
        parts = line.split("|")
        if len(parts) >= 5:
            hash_, author, email, date, *msg_parts = parts
            msg = "|".join(msg_parts)
            lines.append(f"- {hash_[:8]} | {date} | {author} | {msg}")

    return "최근 커밋 목록:\n" + "\n".join(lines) if lines else "커밋 없음"


@tool
def get_commit_info(commit_hash: str) -> str:
    """특정 커밋의 상세 정보(작성자, 날짜, 메시지, 변경 통계)를 가져옵니다.

    Args:
        commit_hash: 커밋 해시 (전체 또는 앞 7-8자리)
    """
    return _run_git([
        "show", commit_hash,
        "--stat",
        "--pretty=format:커밋: %H%n작성자: %an <%ae>%n날짜: %ad%n메시지: %s%n%n상세 설명:%n%b",
        "--date=format:%Y-%m-%d %H:%M:%S",
    ])


@tool
def get_changed_files(commit_hash: str) -> str:
    """특정 커밋에서 변경된 파일 목록과 변경 유형(추가/수정/삭제)을 가져옵니다.

    Args:
        commit_hash: 커밋 해시
    """
    output = _run_git(["show", "--name-status", "--pretty=format:", commit_hash])
    lines = [l for l in output.split("\n") if l.strip()]
    if not lines:
        return "변경된 파일 없음"

    result = []
    for line in lines:
        parts = line.split("\t")
        if len(parts) >= 2:
            status_map = {"A": "추가", "M": "수정", "D": "삭제", "R": "이름변경"}
            status = status_map.get(parts[0][0], parts[0])
            result.append(f"[{status}] {parts[-1]}")
        else:
            result.append(line)
    return "\n".join(result)


@tool
def get_git_diff(commit_hash: str, base: str = "") -> str:
    """특정 커밋의 코드 변경 내용(diff)을 가져옵니다.

    Args:
        commit_hash: 대상 커밋 해시
        base: 비교 기준 커밋/브랜치 (비어있으면 해당 커밋의 이전 커밋과 비교)
    """
    if base:
        diff = _run_git(["diff", base, commit_hash])
    else:
        diff = _run_git(["show", commit_hash, "--no-stat", "-p"])

    if not diff or diff == "[오류]":
        return "변경 사항 없음"

    # 너무 길면 잘라서 반환
    if len(diff) > 8000:
        diff = diff[:8000] + "\n\n... (diff가 길어 앞부분만 표시합니다)"

    return diff
