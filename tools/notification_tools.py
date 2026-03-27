"""
알림 도구 — 코드 변경 관련 담당자를 조회하고 알림을 발송하는 도구들

실제 환경에서는 send_notification 내부에 이메일/Slack API 호출을 추가하세요.
"""

from datetime import datetime
from pathlib import Path

from langchain_core.tools import tool

# ─── 담당자 맵 ────────────────────────────────────────────────
# 파일 경로에 키워드가 포함되면 해당 담당자에게 알림
# 실제 프로젝트에 맞게 수정하세요.
STAKEHOLDER_MAP: dict[str, list[str]] = {
    "auth":     ["김철수 <kim.cs@company.com>", "이영희 <lee.yh@company.com>"],
    "api":      ["박민준 <park.mj@company.com>"],
    "db":       ["최지원 <choi.jw@company.com>", "한상훈 <han.sh@company.com>"],
    "model":    ["최지원 <choi.jw@company.com>"],
    "frontend": ["정수현 <jung.sh@company.com>"],
    "test":     ["이영희 <lee.yh@company.com>"],
    "config":   ["김철수 <kim.cs@company.com>", "박민준 <park.mj@company.com>"],
    "deploy":   ["한상훈 <han.sh@company.com>"],
    "security": ["김철수 <kim.cs@company.com>", "이영희 <lee.yh@company.com>"],
}
DEFAULT_STAKEHOLDERS = ["개발팀 전체 <dev-team@company.com>"]

NOTIFICATIONS_LOG = Path(__file__).parent.parent / "notifications_log.md"


@tool
def get_stakeholders(file_paths: list) -> str:
    """변경된 파일 경로를 기반으로 관련 담당자를 조회합니다.

    Args:
        file_paths: 변경된 파일 경로 목록 (예: ["src/auth/login.py", "api/user.py"])
    """
    stakeholders: set[str] = set()
    mapping_info: list[str] = []

    for file_path in file_paths:
        path_lower = file_path.lower()
        matched = False
        for keyword, people in STAKEHOLDER_MAP.items():
            if keyword in path_lower:
                stakeholders.update(people)
                mapping_info.append(f"  {file_path} → [{keyword}] {', '.join(people)}")
                matched = True
        if not matched:
            stakeholders.update(DEFAULT_STAKEHOLDERS)
            mapping_info.append(f"  {file_path} → [기본] {', '.join(DEFAULT_STAKEHOLDERS)}")

    lines = [f"관련 담당자 ({len(stakeholders)}명):"]
    lines += sorted(stakeholders)
    lines += ["", "매핑 규칙:"] + mapping_info
    return "\n".join(lines)


@tool
def send_notification(recipients: list, subject: str, message: str) -> str:
    """담당자들에게 코드 변경 알림을 전송합니다.
    전송 내역은 notifications_log.md 파일에 기록됩니다.

    Args:
        recipients: 수신자 목록 (예: ["김철수 <kim@company.com>", "이영희 <lee@company.com>"])
        subject: 알림 제목
        message: 알림 본문 내용
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_entry = (
        f"\n---\n"
        f"**전송 시각:** {now}  \n"
        f"**수신자:** {', '.join(recipients)}  \n"
        f"**제목:** {subject}\n\n"
        f"{message}\n"
    )

    # 로그 파일에 기록
    with open(NOTIFICATIONS_LOG, "a", encoding="utf-8") as f:
        f.write(log_entry)

    # 실제 환경에서는 여기서 이메일/Slack API 호출
    # 예: requests.post("https://slack.com/api/chat.postMessage", ...)

    return (
        f"알림 전송 완료!\n"
        f"수신자: {len(recipients)}명 ({', '.join(recipients)})\n"
        f"제목: {subject}\n"
        f"전송 시각: {now}\n"
        f"기록 위치: notifications_log.md\n"
        f"(실제 환경에서는 이메일/Slack으로 전송됩니다)"
    )
