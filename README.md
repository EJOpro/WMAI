# WMAI - Web Management & Analytics Integration

커뮤니티 관리자용 통합 대시보드 및 트렌드 분석 시스템

## 프로젝트 개요

FastAPI 기반의 통합 웹 애플리케이션으로, 커뮤니티 관리, 비윤리/스팸 분석, 트렌드 분석 기능을 제공합니다.

## 주요 기능

### 1. 커뮤니티 관리 대시보드
- **자연어 검색** - 커뮤니티 내 게시글 검색
- **API 콘솔** - API 요청 테스트 인터페이스
- **이탈 분석 대시보드** - 사용자 이탈률 및 세그먼트 분석
- **신고글 분류평가** - 카테고리별 신고 통계

### 2. Ethics 분석 시스템
- **비윤리/스팸지수 평가** - AI 기반 텍스트 분석
- **하이브리드 분석** - 규칙 기반 + ML 모델 결합
- **로그 대시보드** - 분석 이력 조회 및 통계
- **실시간 분석 API** - `/api/ethics/analyze` 엔드포인트

### 3. 이탈 분석 대시보드 (Churn Analysis)
- **CSV 데이터 업로드** - 사용자 이벤트 데이터 업로드
- **기간별 분석** - 특정 기간 동안의 이탈률 분석
- **세그먼트 분석** - 성별, 연령대, 채널별 세그먼트 분석
- **시각화** - 차트와 지표를 통한 분석 결과 표시
- **LLM 통합** - AI 기반 분석 인사이트 제공

### 4. 트렌드 분석 시스템 (TrendStream)
- **실시간 트렌드 수집** - dad.dothome.co.kr API 연동
- **키워드 정규화** - 자연어 → 표준 키워드 변환
- **타임라인 분석** - 날짜별 검색 트렌드 추적
- **증감률 계산** - 키워드 인기도 변화 분석
- **게시글/댓글 통계** - 커뮤니티 활동 지표

## 기술 스택

- **백엔드**: FastAPI 0.115+, Python 3.11+
- **템플릿**: Jinja2 3.1+
- **프론트엔드**: HTML5, CSS3, Vanilla JavaScript
- **HTTP 클라이언트**: httpx 0.24+
- **데이터베이스**: MySQL (PyMySQL), Redis 5.0+
- **ML/NLP**: PyTorch, Transformers, scikit-learn
- **백그라운드 작업**: APScheduler 3.10+
- **로깅**: Loguru 0.7+

## 설치 및 실행

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정

```bash
# ethics/.env 파일 생성
cp ethics/.env.example ethics/.env
# 또는 수동으로 생성:
# OPENAI_API_KEY=your_api_key_here
```

### 3. 개발 서버 실행

#### 메인 애플리케이션 (포트 8000)

```bash
# 방법 1: uvicorn 직접 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 방법 2: Python 스크립트 실행
python run_server.py
```

#### TrendStream 백엔드 (포트 8001)

```bash
cd trend
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8001
```

### 4. 브라우저에서 접속

- **메인 대시보드**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs
- **TrendStream API**: http://localhost:8001/docs
- **TrendStream 대시보드**: http://localhost:8001/public/dad_dashboard.html

## 폴더 구조

```
WMAI/
├── app/                        # 메인 애플리케이션
│   ├── main.py                 # FastAPI 엔트리포인트
│   ├── settings.py             # 환경 설정
│   ├── api/
│   │   ├── routes_api.py       # API 엔드포인트 (실제 트렌드 API 포함)
│   │   ├── routes_public.py    # 페이지 라우팅
│   │   └── routes_health.py    # 헬스체크
│   ├── templates/              # Jinja2 템플릿
│   │   ├── base.html
│   │   ├── components/
│   │   └── pages/
│   └── static/                 # 정적 파일 (CSS, JS, 이미지)
│
├── ethics/                     # Ethics 분석 시스템
│   ├── ethics_hybrid_predictor.py  # 하이브리드 분석기
│   ├── ethics_db_logger.py     # 로그 관리
│   ├── ethics_predict.py       # 예측 모델
│   ├── ethics_train_model.py   # 모델 학습
│   └── models/                 # ML 모델 설정
│
├── chrun_backend/              # 이탈 분석 백엔드 로직
│   ├── chrun_main.py           # FastAPI 라우터
│   ├── chrun_analytics.py      # 분석 엔진
│   ├── chrun_models.py         # 데이터베이스 모델
│   ├── chrun_schemas.py        # API 스키마
│   └── chrun_database.py       # 데이터베이스 연결
│
├── chrun_dashboard/            # 프론트엔드 대시보드
│   ├── churn.html              # 메인 대시보드 화면
│   ├── chrun_styles.css        # 스타일시트
│   ├── chrun_script.js         # 프론트엔드 로직
│   └── chrun_api_client.js     # API 통신 로직
│
├── trend/                      # TrendStream 백엔드
│   ├── backend/
│   │   ├── main.py             # TrendStream API 서버
│   │   ├── api/                # 각종 API 라우트
│   │   ├── services/           # 비즈니스 로직
│   │   └── workers/            # 백그라운드 작업
│   ├── config/                 # 설정
│   ├── public/                 # 대시보드 HTML/JS
│   └── db/                     # 데이터베이스 스키마
│
├── requirements.txt            # 통합 의존성 목록
├── run_server.py               # 서버 실행 스크립트
└── README.md
```

## API 엔드포인트

### 메인 애플리케이션 (포트 8000)

#### 검색 & 분석
- `GET /api/search?q={query}` - 자연어 검색
- `GET /api/trends?limit={limit}` - 실시간 트렌드 데이터 (외부 API 연동)
- `GET /api/metrics/bounce` - 이탈률 데이터
- `GET /api/reports/moderation` - 신고 분류 데이터

#### Ethics 분석
- `POST /api/ethics/analyze` - 텍스트 비윤리/스팸 분석
- `GET /api/ethics/logs` - 분석 로그 조회
- `GET /api/ethics/logs/stats` - 통계 정보
- `DELETE /api/ethics/logs/{log_id}` - 로그 삭제
- `DELETE /api/ethics/logs/batch/old` - 오래된 로그 일괄 삭제

#### 이탈 분석 API
- `POST /api/churn/upload` - CSV 데이터 업로드
- `GET /api/churn/analyze` - 이탈률 분석 실행
- `GET /api/churn/metrics` - 월별 지표 조회
- `GET /api/churn/segments` - 세그먼트별 분석 결과

#### 프론트엔드 라우트
- `GET /` - 메인 페이지
- `GET /api-console` - API 콘솔
- `GET /churn` - 이탈 분석 대시보드
- `GET /trends` - 트렌드 대시보드
- `GET /reports` - 신고글 분류
- `GET /ethics_analyze` - 비윤리/스팸지수 평가
- `GET /ethics_dashboard` - Ethics 로그 대시보드
- `GET /health` - 헬스체크

### TrendStream API (포트 8001)

- `GET /v1/trends/popular` - 인기 검색어 조회
- `GET /v1/stats/board` - 게시판 통계
- `POST /v1/ingest/event` - 이벤트 수집
- `GET /v1/analytics/keywords` - 키워드 분석
- `GET /health` - 헬스체크

## 주요 기능 설명

### 실시간 트렌드 API 연동

`/api/trends` 엔드포인트는 외부 API (dad.dothome.co.kr)에서 실제 데이터를 가져옵니다:

1. **키워드 정규화** - "검색했음" → "검색" 등 자연어를 표준 키워드로 변환
2. **날짜별 집계** - 타임라인 데이터 생성
3. **증감률 계산** - 이전 날짜와 비교하여 트렌드 변화 분석
4. **Mock Fallback** - API 오류 시 현실적인 Mock 데이터 반환

### Ethics 분석 시스템

하이브리드 방식으로 텍스트의 비윤리성과 스팸 여부를 분석:

1. **규칙 기반 분석** - 사전 정의된 패턴 매칭
2. **ML 모델 분석** - PyTorch 기반 딥러닝 모델
3. **OpenAI API** - GPT를 활용한 고급 분석
4. **로그 저장** - MySQL 데이터베이스에 분석 이력 저장

## 개발 가이드

### 코드 규칙

1. API 엔드포인트 추가 시 `routes_api.py`에 작성
2. 페이지 라우트 추가 시 `routes_public.py`에 작성
3. 공용 스타일은 `app/static/css/app.css`에 추가
4. JavaScript는 `app/static/js/app.js`에 공통 함수 작성
5. 템플릿은 `base.html`을 상속하여 작성

### API 통합

JavaScript에서 API 호출:

```javascript
const data = await apiRequest('/api/trends?limit=50');
console.log(data.keywords);
```

### 이탈 분석 대시보드 통합

#### 접근 방법
1. 홈페이지(`/`) 접속
2. "이탈 분석 대시보드" 카드의 "이탈 분석 대시보드" 버튼 클릭
3. 이탈 분석 대시보드(`/churn`) 페이지로 이동

#### 사용 흐름
1. CSV 파일 업로드 (user_hash, created_at, action, gender, age_band, channel 컬럼 필요)
2. 분석 기간 설정 (시작일, 종료일)
3. 세그먼트 선택 (성별, 연령대, 채널)
4. "분석 실행" 버튼 클릭
5. 이탈률, 활성 사용자 수, 장기 미접속 사용자 등 지표 확인
6. 차트를 통한 시각적 분석 결과 확인

### Ethics 분석 사용 예시

```python
from ethics.ethics_hybrid_predictor import HybridEthicsAnalyzer

analyzer = HybridEthicsAnalyzer()
result = analyzer.analyze("분석할 텍스트")
print(f"비윤리 점수: {result['final_score']}")
```

## 배포

### Docker Compose (TrendStream)

```bash
cd trend
docker-compose up -d
```

### 운영 서버 실행

```bash
# 메인 앱
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# TrendStream
cd trend
uvicorn backend.main:app --host 0.0.0.0 --port 8001 --workers 2
```

## 라이선스

MIT License

## 기여

프로젝트에 기여하시려면 Pull Request를 생성해주세요.

---

**통합 완료일**: 2025-10-28  
**버전**: 2.0.0 (A + B 통합)
