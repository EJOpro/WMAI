# WMAI-feature-match 프로젝트 통합 문서

## 📁 프로젝트 구조

```
WMAI-feature-match/
├── app/                           # 메인 애플리케이션
│   ├── main.py                    # FastAPI 앱 진입점
│   ├── settings.py                # 설정
│   ├── api/                       # API 라우터
│   │   ├── routes_public.py       # 페이지 라우팅
│   │   ├── routes_health.py       # 헬스체크
│   │   ├── routes_api.py          # Mock API (기본 기능)
│   │   └── routes_match.py        # WMAA 신고 검증 API ⭐
│   ├── templates/                 # Jinja2 템플릿
│   │   ├── base.html
│   │   ├── components/
│   │   └── pages/
│   │       ├── home.html          # 메인 페이지
│   │       ├── reports.html       # WMAA 신고 검증 페이지 ⭐
│   │       ├── reports_admin.html # WMAA 관리자 페이지 ⭐
│   │       ├── api_console.html
│   │       ├── bounce.html
│   │       ├── trends.html
│   │       └── hate.html
│   └── static/                    # 정적 파일
│       ├── css/
│       │   ├── app.css
│       │   ├── match_main.css     # WMAA 메인 스타일 ⭐
│       │   └── match_admin_styles.css # WMAA 관리자 스타일 ⭐
│       ├── js/
│       │   ├── app.js
│       │   ├── match_main.js      # WMAA 메인 JS ⭐
│       │   └── match_admin_script.js # WMAA 관리자 JS ⭐
│       └── img/
│
├── match_backend/                 # WMAA 백엔드 모듈 ⭐
│   ├── __init__.py                # 모듈 초기화
│   ├── core.py                    # 핵심 비즈니스 로직
│   ├── models.py                  # Pydantic 데이터 모델
│   └── README.md                  # WMAA 백엔드 문서
│
├── config.env.example             # 환경 변수 예시
├── match_reports_db.json          # 신고 데이터 (자동 생성)
├── requirements.txt               # Python 패키지
├── README.md                      # 프로젝트 문서
├── INTEGRATION.md                 # 이 파일
└── run_server.py                  # 서버 실행 스크립트
```

## 🔄 통합 방식

### 1. 프론트엔드 통합 (app/templates/pages/)
- **reports.html**: 사용자가 만든 신고 검증 페이지
- **reports_admin.html**: 사용자가 만든 관리자 대시보드
- home.html의 57번째 줄 "이동" 버튼이 `/reports`로 연결됨

### 2. 백엔드 분리 (match_backend/)
- 사용자가 만든 백엔드 로직이 별도 모듈로 분리됨
- `app/api/routes_match.py`가 `match_backend`의 함수들을 import하여 사용
- 스켈레톤 코드의 기존 API(`routes_api.py`)와 독립적으로 작동

### 3. API 라우팅
```python
# app/main.py
from app.api import routes_public, routes_health, routes_api, routes_match

app.include_router(routes_public.router)      # 페이지 라우팅
app.include_router(routes_health.router)      # 헬스체크
app.include_router(routes_api.router, prefix="/api")  # Mock API
app.include_router(routes_match.router, prefix="/api") # WMAA API
```

## 🌐 주요 엔드포인트

### 페이지 라우트
- `GET /` - 메인 페이지
- `GET /reports` - WMAA 신고 검증 페이지
- `GET /reports/admin` - WMAA 관리자 대시보드
- `GET /api-console` - API 콘솔
- `GET /bounce` - 이탈률 분석
- `GET /trends` - 트렌드 분석
- `GET /hate` - 혐오지수 평가

### WMAA API 엔드포인트
- `POST /api/analyze` - AI 신고 분석
- `GET /api/examples` - 예시 데이터
- `GET /api/reports/list` - 신고 목록
- `GET /api/reports/detail/{id}` - 신고 상세
- `PUT /api/reports/update/{id}` - 신고 상태 업데이트
- `GET /api/reports/stats` - 통계 데이터

## 🔧 설정 및 실행

### 1. 환경 변수 설정
```bash
cp config.env.example config.env
# config.env 파일에 OpenAI API 키 입력
```

### 2. 패키지 설치
```bash
pip install -r requirements.txt
```

### 3. 서버 실행
```bash
# 방법 1
python run_server.py

# 방법 2
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. 접속
- 메인: http://localhost:8000
- WMAA 신고 검증: http://localhost:8000/reports
- WMAA 관리자: http://localhost:8000/reports/admin
- API 문서: http://localhost:8000/docs

## 🗄️ 데이터베이스

### JSON 파일 기반 저장
- 파일: `match_reports_db.json`
- 위치: 프로젝트 루트
- 자동 생성: 첫 신고 저장 시
- Git 제외: `.gitignore`에 포함

### 데이터 구조
```json
[
  {
    "id": 1,
    "reportDate": "2025-10-29T10:30:00",
    "reportType": "욕설 및 비방",
    "reportedContent": "게시글 내용",
    "reportReason": "욕설 및 비방",
    "reporterId": "fastapi_user",
    "aiAnalysis": {
      "result": "일치",
      "confidence": 92,
      "analysis": "분석 내용"
    },
    "status": "completed",
    "priority": "high",
    "assignedTo": "AI_System",
    "processedDate": "2025-10-29T10:30:05",
    "processingNote": "AI 자동 처리",
    "postStatus": "deleted",
    "postAction": "게시글이 자동 삭제되었습니다."
  }
]
```

## 🎨 디자인 유지

### 사용자 기존 디자인 보존
- WMAA의 모든 CSS/JS 파일이 그대로 유지됨
- `match_main.css`, `match_admin_styles.css`
- `match_main.js`, `match_admin_script.js`
- Bootstrap 5.3.0 사용
- Font Awesome 6.4.0 사용

## 🔐 보안

### 환경 변수
- `config.env`: OpenAI API 키 저장
- Git에서 제외됨 (`.gitignore`)

### API 키 확인
```python
# match_backend/core.py
from openai import OpenAI
client = OpenAI()  # 환경 변수에서 자동으로 API 키 로드
```

## 📊 처리 로직

### AI 분석 결과에 따른 자동 처리
1. **일치 (Match)**
   - 상태: `completed`
   - 게시글: 자동 삭제
   - 우선순위: `high`

2. **불일치 (Mismatch)**
   - 상태: `rejected`
   - 게시글: 자동 유지
   - 우선순위: `low`

3. **부분일치 (Partial)**
   - 상태: `pending`
   - 게시글: 검토 대기
   - 우선순위: `medium`
   - 관리자 수동 처리 필요

## 🚀 확장 가능성

### 향후 개선 방향
1. SQLite/PostgreSQL 등 실제 DB로 마이그레이션
2. 사용자 인증 시스템 추가
3. 실시간 알림 기능
4. 대시보드 차트 데이터 실시간 업데이트
5. 신고 유형 커스터마이징

## 📝 주요 변경 사항

### 스켈레톤 코드에 추가된 내용
1. `match_backend/` 폴더 및 모듈
2. `app/api/routes_match.py` 라우터
3. `app/templates/pages/reports.html`
4. `app/templates/pages/reports_admin.html`
5. WMAA 관련 CSS/JS 파일들
6. `requirements.txt`에 `openai` 패키지 추가

### 수정된 파일
1. `app/main.py` - routes_match 등록
2. `app/api/routes_public.py` - /reports/admin 라우트 추가
3. `.gitignore` - config.env, match_reports_db.json 제외
4. `README.md` - WMAA 사용 가이드 추가

## ✅ 통합 완료 체크리스트

- [x] match_backend 모듈 생성
- [x] routes_match.py API 라우터 생성
- [x] 프론트엔드 페이지 통합 (reports.html, reports_admin.html)
- [x] 정적 파일 복사 (CSS, JS)
- [x] app/main.py에 라우터 등록
- [x] OpenAI API 연동
- [x] JSON 기반 DB 연동
- [x] 예시 데이터 API
- [x] 관리자 기능 (상태 업데이트)
- [x] 통계 API
- [x] 문서화 (README.md, INTEGRATION.md)
- [x] .gitignore 설정

## 🎓 사용 가이드

### 신고 검증 프로세스
1. `/reports` 페이지 접속
2. 신고된 게시글 내용 입력
3. 신고 사유 선택
4. "일치 여부 분석" 버튼 클릭
5. AI 분석 결과 확인
6. 자동 처리 또는 관리자 검토

### 관리자 대시보드 사용
1. `/reports/admin` 페이지 접속
2. 대시보드에서 통계 확인
3. 신고 목록 탭에서 필터링
4. 부분일치 신고에 대해 승인/반려 처리
5. CSV로 데이터 내보내기 가능

## 🤝 기여

프로젝트 개선 사항이나 버그 리포트는 이슈로 등록해주세요.

## 📄 라이선스

MIT License

