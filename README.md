# diffwatch

> GitHub 커밋을 자동으로 감지하여 코드 변경 영향도를 분석하고,
> 관련 담당자에게 알림을 발송하는 AI 에이전트

## 주요 기능

- **자동 감지** — GitHub Webhook으로 push 이벤트를 실시간 수신
- **영향도 분석** — git diff를 분석하여 변경 수준을 높음 / 중간 / 낮음으로 판정
- **담당자 알림** — 변경된 파일 경로 기반으로 담당자를 자동 매핑하여 알림 발송
- **변경 이력 기억** — 분석 결과를 RAG에 저장, 이후 자연어 질문으로 조회 가능
- **관리자 대시보드** — 커밋 분석 현황 및 알림 이력을 웹 UI로 확인
- **내장 챗봇** — 대시보드 안에서 에이전트와 실시간 스트리밍 대화

## 아키텍처

```
GitHub push
    │
    ▼
webhook_server.py        ← FastAPI, POST /webhook + 대시보드 서빙
    │
    ▼
agent.py                 ← LangGraph 기반 에이전트
    ├── tools/
    │   ├── git_tools.py              커밋 정보 / diff 조회
    │   ├── notification_tools.py     담당자 조회 / 알림 발송
    │   └── change_memory_tools.py    분석 결과 저장 / 조회
    ├── rag/retriever.py              변경 이력 벡터 검색
    └── skills/code-impact-analysis/  분석 절차 및 영향도 기준

frontend/                ← 관리자 대시보드 (HTML / CSS / JS)
    ├── index.html        대시보드 · 커밋 분석 · 알림 이력 · 챗봇 패널
    ├── style.css
    └── app.js
```

## 시작하기

### 요구사항

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- OpenAI API 키
- ngrok (로컬 환경에서 GitHub Webhook 테스트 시)

### 설치

```bash
git clone https://github.com/wizdom972/POSCODX-diffwatch.git
cd POSCODX-diffwatch
uv sync
```

### 환경 변수 설정

`.env` 파일을 생성하고 아래 값을 입력합니다.

```bash
# 필수
OPENAI_API_KEY=sk-...

# 분석 대상 git 저장소 경로 (없으면 현재 디렉토리 사용)
TARGET_REPO_PATH=/path/to/your/repo

# GitHub Webhook Secret (GitHub 설정값과 동일하게)
GITHUB_WEBHOOK_SECRET=your-secret-string
```

### 실행

**대시보드 + Webhook 서버**
```bash
uv run fastapi dev webhook_server.py --port 8001
# → http://localhost:8001
```

**로컬 테스트 시 ngrok으로 외부 URL 발급**
```bash
ngrok http 8001
# → https://xxxx.ngrok-free.app
```

## 대시보드

`http://localhost:8001` 접속 시 아래 화면을 제공합니다.

| 페이지 | 내용 |
|--------|------|
| 대시보드 | 통계 카드 (총 분석 커밋 / 영향도별 / 발송 알림) + 최근 커밋 목록 |
| 커밋 분석 | 전체 커밋 목록, 클릭 시 상세 모달 (파일 목록 · 담당자 · 분석 내용) |
| 알림 이력 | 발송된 알림 카드 (수신자 · 제목 · 본문) |
| 💬 챗봇 | 우측 하단 FAB 클릭 → 슬라이드 패널에서 에이전트와 실시간 대화 |

## GitHub Webhook 등록

GitHub 저장소 → **Settings → Webhooks → Add webhook**

| 항목 | 값 |
|------|-----|
| Payload URL | `https://xxxx.ngrok-free.app/webhook` |
| Content type | `application/json` |
| Secret | `.env`의 `GITHUB_WEBHOOK_SECRET` 값 |
| Events | Just the push event |

## 담당자 맵 설정

`tools/notification_tools.py`의 `STAKEHOLDER_MAP`을 프로젝트에 맞게 수정합니다.
파일 경로에 키워드가 포함되면 해당 담당자에게 알림이 발송됩니다.

```python
STAKEHOLDER_MAP = {
    "auth":     ["홍길동 <hong@company.com>"],
    "api":      ["김철수 <kim@company.com>"],
    "db":       ["이영희 <lee@company.com>"],
    "frontend": ["박민준 <park@company.com>"],
}
```

## 챗봇 사용 예시

```
최근 커밋 목록 보여줘
abc1234 커밋 영향도 분석해줘
auth 관련해서 어떤 변경이 있었어?
DB 스키마 바뀐 커밋이 뭐였지?
```

## 발송 이력 확인

```bash
cat notifications_log.md                        # 알림 발송 이력
cat rag/documents/code_changes_log.md           # 코드 변경 분석 이력
```

## 기술 스택

| 항목 | 기술 |
|------|------|
| LLM | OpenAI GPT-4o mini |
| 에이전트 프레임워크 | DeepAgents + LangGraph |
| RAG | LangChain + OpenAI Embeddings |
| Webhook 서버 / 대시보드 API | FastAPI |
| 대시보드 UI | HTML / CSS / JS |
| 패키지 관리 | uv |
