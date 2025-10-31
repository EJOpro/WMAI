# Community Admin Frontend

커뮤니티 관리자용 API 서비스 프론트엔드 대시보드

## 프로젝트 개요

FastAPI + Jinja2 기반의 SSR 웹 애플리케이션으로, 커뮤니티 관리자가 다양한 데이터를 시각적으로 확인하고 관리할 수 있는 대시보드입니다.

## 주요 기능

1. **자연어 검색** - 커뮤니티 내 게시글 검색
2. **API 콘솔** - API 요청 테스트 인터페이스
3. **방문객 이탈률 대시보드** - 이탈률 데이터 시각화
4. **트렌드 대시보드** - 트렌드 및 키워드 분석
5. **신고글 분류평가** (WMAA 통합) - AI 기반 신고글과 신고유형 일치 여부 검증
   - OpenAI GPT-4o-mini를 활용한 자동 분석
   - 신고 내용과 게시글의 일치/불일치/부분일치 판단
   - 관리자 대시보드를 통한 신고 내역 관리
   - 자동 게시글 처리 (일치 시 삭제, 불일치 시 유지, 부분일치 시 검토 대기)
6. **혐오지수 평가** - 텍스트 혐오 표현 분석

## 기술 스택

- **백엔드**: FastAPI 0.115+
- **템플릿**: Jinja2 3.1+
- **프론트엔드**: HTML5, CSS3, Vanilla JavaScript
- **서버**: Uvicorn 0.30+
- **언어**: Python 3.11+

## 설치 및 실행

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정

```bash
cp config.env.example match_config.env
```

`match_config.env` 파일을 수정하여 OpenAI API 키를 설정합니다:

```bash
OPENAI_API_KEY=sk-proj-your-actual-openai-api-key-here
```

**OpenAI API 키 발급 방법:**
1. https://platform.openai.com/api-keys 접속
2. "Create new secret key" 클릭하여 API 키 생성
3. 생성된 키를 `match_config.env` 파일에 입력

**API 키 테스트:**
```bash
python test_api_key.py
```

### 3. 개발 서버 실행

```bash
# 방법 1: uvicorn 직접 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 방법 2: Python 모듈로 실행
python -m app.main
```

### 4. 브라우저에서 접속

```
http://localhost:8000
```

## 폴더 구조

```
app/
├── main.py                 # FastAPI 엔트리포인트
├── settings.py             # 환경 설정
├── api/
│   ├── routes_public.py    # 페이지 라우팅
│   └── routes_health.py    # 헬스체크
├── templates/
│   ├── base.html           # 기본 레이아웃
│   ├── components/         # 재사용 컴포넌트
│   │   ├── nav.html
│   │   ├── footer.html
│   │   └── alert.html
│   └── pages/              # 페이지 템플릿
│       ├── home.html
│       ├── api_console.html
│       ├── bounce.html
│       ├── trends.html
│       ├── reports.html
│       └── hate.html
└── static/
    ├── css/
    │   └── app.css         # 스타일시트
    ├── js/
    │   └── app.js          # JavaScript 로직
    └── img/                # 이미지 리소스
```

## API 엔드포인트

### 백엔드 API (외부)

- `GET /api/search?q={query}` - 자연어 검색
- `GET /api/metrics/bounce` - 이탈률 데이터
- `GET /api/trends` - 트렌드 데이터
- `GET /api/reports/moderation` - 신고 분류 데이터
- `POST /api/moderation/hate-score` - 혐오지수 분석

### WMAA 신고 검증 API

- `POST /api/analyze` - 신고 내용 AI 분석
- `GET /api/examples` - 신고 예시 데이터
- `GET /api/reports/list` - 신고 목록 조회
- `GET /api/reports/detail/{report_id}` - 특정 신고 상세 조회
- `PUT /api/reports/update/{report_id}` - 신고 상태 업데이트

### 프론트엔드 라우트

- `GET /` - 메인 페이지
- `GET /api-console` - API 콘솔
- `GET /bounce` - 이탈률 대시보드
- `GET /trends` - 트렌드 대시보드
- `GET /reports` - 신고글 검증 (WMAA)
- `GET /reports/admin` - 신고 관리 대시보드 (WMAA)
- `GET /hate` - 혐오지수 평가
- `GET /health` - 헬스체크

## 개발 가이드

### Git 브랜치 전략

- `main`: 안정화 버전 (배포용)
- `feature/*`: 신규 기능 개발
- `fix/*`: 버그 수정

### 코드 규칙

1. 페이지 추가 시 `routes_public.py`에 라우트 등록
2. 공용 스타일은 `app.css`에 추가
3. JavaScript는 `app.js`에 공통 함수 작성
4. 템플릿은 `base.html`을 상속하여 작성

### API 통합

모든 API 호출은 `app.js`의 `apiRequest()` 함수를 사용:

```javascript
const data = await apiRequest('/api/search?q=test');
```

## 배포

### 운영 서버 실행

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Docker 배포 (선택사항)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## WMAA 신고 검증 시스템 사용 가이드

### 신고 검증 페이지 (`/reports`)

1. 신고된 게시글 내용을 입력
2. 신고 사유 선택 (욕설 및 비방, 도배 및 광고, 사생활 침해, 저작권 침해)
3. "일치 여부 분석" 버튼 클릭
4. AI 분석 결과 확인:
   - **일치**: 신고 내용이 게시글과 일치 → 게시글 자동 삭제
   - **불일치**: 신고 내용이 게시글과 불일치 → 게시글 자동 유지
   - **부분일치**: 판단이 애매한 경우 → 관리자 검토 대기

### 신고 관리 대시보드 (`/reports/admin`)

1. **대시보드 탭**: 신고 통계 및 처리 현황 확인
2. **신고 목록 탭**: 
   - 모든 신고 내역 조회
   - 필터링: 상태별, 유형별, 기간별
   - 부분일치 신고에 대한 승인/반려 처리
3. **통계 분석 탭**: 월별 트렌드 및 처리 시간 분석

### 데이터 저장

신고 데이터는 `match_reports_db.json` 파일에 저장됩니다. 이 파일은 `.gitignore`에 포함되어 있어 Git에 커밋되지 않습니다.

## 라이선스

MIT License

## 기여

프로젝트에 기여하시려면 Pull Request를 생성해주세요.

## 문의

WMAA 통합 관련 문의사항이 있으시면 이슈를 등록해주세요.

