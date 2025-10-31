# WMAA Backend

신고글과 신고유형의 일치 여부를 AI로 확인하는 시스템의 백엔드 모듈입니다.

## 구조

```
match_backend/
├── __init__.py          # 모듈 초기화
├── core.py              # 핵심 비즈니스 로직 (AI 분석, DB 처리)
├── models.py            # Pydantic 데이터 모델
└── README.md            # 이 파일
```

## 주요 기능

### 1. AI 분석 (`analyze_with_ai`)
- OpenAI GPT-4o-mini를 사용하여 신고 내용과 게시글 일치 여부 분석
- 반환값: 점수, 판단(일치/불일치/부분일치), 분석 내용

### 2. 데이터베이스 처리
- `load_reports_db()`: 신고 데이터 로드
- `save_reports_db()`: 신고 데이터 저장
- `save_report_to_db()`: 새 신고 저장
- `update_report_status()`: 신고 상태 업데이트
- `get_report_by_id()`: ID로 신고 조회

### 3. 자동 처리 로직
- **일치**: 신고 내용과 게시글이 일치 → 게시글 자동 삭제
- **불일치**: 신고 내용과 게시글이 불일치 → 게시글 자동 유지
- **부분일치**: 판단이 애매한 경우 → 관리자 검토 대기

## 사용 예제

```python
from match_backend import analyze_with_ai, save_report_to_db

# AI 분석
result = analyze_with_ai(
    post="게시글 내용",
    reason="욕설 및 비방"
)

# DB에 저장
saved_report = save_report_to_db(
    post_content="게시글 내용",
    reason="욕설 및 비방",
    ai_result=result
)
```

## 설정

### OpenAI API 키
프로젝트 루트의 `match_config.env` 파일에 설정:
```
OPENAI_API_KEY=sk-proj-your-actual-api-key-here
```

**테스트 방법:**
```bash
python test_api_key.py
```

## 데이터 저장
신고 데이터는 프로젝트 루트의 `match_reports_db.json` 파일에 JSON 형식으로 저장됩니다.

## 라이선스
MIT License
