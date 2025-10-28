# Community Admin Frontend

커뮤니티 관리자용 API 서비스 프론트엔드 대시보드

## 프로젝트 개요

FastAPI + Jinja2 기반의 SSR 웹 애플리케이션으로, 커뮤니티 관리자가 다양한 데이터를 시각적으로 확인하고 관리할 수 있는 대시보드입니다.

## 주요 기능

1. **자연어 검색** - 커뮤니티 내 게시글 검색
2. **API 콘솔** - API 요청 테스트 인터페이스
3. **방문객 이탈률 대시보드** - 이탈률 데이터 시각화
4. **트렌드 대시보드** - 트렌드 및 키워드 분석
5. **신고글 분류평가** - 카테고리별 신고 통계
6. **비윤리/스팸지수 평가** - 텍스트 비윤리 표현 및 스팸 분석

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
cp .env.example .env
```

`.env` 파일을 수정하여 필요한 설정을 입력합니다.

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
│       ├── ethics_analyze.html
│       └── ethics_dashboard.html
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
- `POST /api/moderation/ethics-score` - 비윤리/스팸지수 분석

### 프론트엔드 라우트

- `GET /` - 메인 페이지
- `GET /api-console` - API 콘솔
- `GET /bounce` - 이탈률 대시보드
- `GET /trends` - 트렌드 대시보드
- `GET /reports` - 신고글 분류
- `GET /ethics_analyze` - 비윤리/스팸지수 평가 입력
- `GET /ethics_dashboard` - 로그기록 대시보드
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

## 라이선스

MIT License

## 기여

프로젝트에 기여하시려면 Pull Request를 생성해주세요.

