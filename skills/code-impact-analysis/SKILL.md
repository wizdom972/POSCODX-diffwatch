---
name: code-impact-analysis
description: git 커밋의 코드 변경 영향도를 분석하고 담당자에게 알림을 보내는 스킬입니다. "영향도 분석", "커밋 분석", "코드 변경 알림", "변경 사항 분석", "diff 분석"과 같은 요청에 활성화됩니다.
---

## 코드 영향도 분석 스킬

### 분석 절차 (반드시 순서대로 실행)

1. **커밋 정보 수집** → `get_commit_info(commit_hash)`
2. **변경 파일 확인** → `get_changed_files(commit_hash)`
3. **코드 diff 분석** → `get_git_diff(commit_hash)`
4. **영향도 판정** → 아래 기준 참고
5. **담당자 조회** → `get_stakeholders(file_paths)`
6. **알림 발송** → `send_notification(recipients, subject, message)`
7. **분석 저장** → `save_change_analysis(...)` ← 반드시 마지막에 실행

### 영향도 판정 기준

| 수준 | 해당 변경 |
|------|-----------|
| **높음** | 핵심 비즈니스 로직, DB 스키마, API 인터페이스, 보안 코드, 인증/인가 |
| **중간** | 기존 기능 수정, 설정 파일, 의존성 추가/변경, 공통 유틸리티 |
| **낮음** | 버그 수정, 리팩토링, 문서 수정, 테스트 코드, 스타일 변경 |

### 알림 메시지 형식

```
[코드 영향도 알림] {short_hash} — 영향도: {impact_level}

담당자님,

담당 영역에 영향을 주는 코드 변경이 있어 안내드립니다.

■ 커밋:    {commit_hash}
■ 작성자:  {author}
■ 날짜:    {date}
■ 요약:    {commit_message}
■ 영향도:  {impact_level}

변경된 파일:
{file_list}

영향 분석:
{analysis_summary}

확인 부탁드립니다.
```

### 최종 보고서 형식

분석이 완료되면 아래 형식으로 결과를 출력하세요.

```
## 코드 영향도 분석 보고서

| 항목 | 내용 |
|------|------|
| 커밋 | {short_hash} |
| 영향도 | {impact_level} |
| 변경 파일 수 | {count}개 |
| 알림 발송 | {recipients_count}명 |

### 주요 변경 사항
{summary}

### 영향 받는 영역
{affected_areas}

### 권고 사항
{recommendations}
```
