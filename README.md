# WMAI - Web Management & Analytics Integration

커뮤니티 관리자용 통합 대시보드 및 트렌드 분석 시스템

## 프로젝트 개요

FastAPI 기반의 통합 웹 애플리케이션으로, AI Agent Chatbot, 커뮤니티 관리, 비윤리/스팸 분석, 트렌드 분석 기능을 제공합니다.

## 주요 기능

### 1. AI Agent Chatbot ⭐ (신규)
- **LangGraph 기반** - ReAct 패턴의 자율 에이전트
- **의미 기반 검색** - BGE-M3 임베딩 + ChromaDB 벡터 검색
- **자동 도구 선택** - 질문 분석 후 15개 도구 중 최적 도구 자동 실행
- **대화형 인터페이스** - 자연어로 커뮤니티 관리 작업 수행
- **게시판 조작** - 필터링, 정렬, 페이지 이동, 상세보기
- **분석 자동화** - 이탈률, 비윤리, 신고, 트렌드 분석 통합
- **일일 보고서** - 커뮤니티 현황 요약 리포트 생성

### 2. 커뮤니티 관리 대시보드
- **게시판 관리** - 게시글/댓글 작성, 수정, 삭제
- **이미지 첨부** - 게시글당 최대 5개 이미지 업로드 (5MB 제한)
- **실시간 검색** - 제목, 내용, 작성자 필터링
- **카테고리 분류** - 자유/질문/정보 게시판
- **API 콘솔** - API 요청 테스트 인터페이스
- **이탈 분석 대시보드** - 사용자 이탈률 및 세그먼트 분석
- **신고글 분류평가** - 카테고리별 신고 통계

### 3. Ethics 분석 시스템 (고도화)
- **비윤리/스팸지수 평가** - AI 기반 텍스트/이미지 분석
- **하이브리드 분석** - KcBERT + LLM(GPT-4.1-nano) + 규칙 기반 결합
- **이미지 분석** - NSFW 감지 + Vision API 2차 검증 (비용 50% 절감)
- **RAG 시스템** - 유사 사례 검색 및 점수 보정
  - ChromaDB 벡터 데이터베이스 활용
  - OpenAI Embeddings (text-embedding-3-small)
  - 관리자 확정 사례 우선 참조
- **즉시 차단** - 고신뢰도 확정 사례와 유사 시 LLM 건너뛰기
- **배치 처리** - OpenAI API 호출 최적화 (4-6배 속도 향상)
- **비동기 저장** - 벡터DB 저장 백그라운드 처리 (1-5초 단축)
- **로그 대시보드** - 분석 이력 조회 및 RAG 상세 통계
- **실시간 분석 API** - `/api/ethics/analyze` 엔드포인트

### 4. 이탈 분석 대시보드 (Churn Analysis)
- **CSV 데이터 업로드** - 사용자 이벤트 데이터 업로드
- **기간별 분석** - 특정 기간 동안의 이탈률 분석
- **세그먼트 분석** - 성별, 연령대, 채널별 세그먼트 분석
- **시각화** - 차트와 지표를 통한 분석 결과 표시
- **LLM 통합** - AI 기반 분석 인사이트 제공
- **RAG 분석** - 이탈 패턴 유사 사례 검색 및 인사이트

### 5. 트렌드 분석 시스템 (TrendStream)
- **실시간 트렌드 수집** - dad.dothome.co.kr API 연동
- **키워드 정규화** - 자연어 → 표준 키워드 변환
- **타임라인 분석** - 날짜별 검색 트렌드 추적
- **증감률 계산** - 키워드 인기도 변화 분석
- **게시글/댓글 통계** - 커뮤니티 활동 지표

### 6. WMAA 신고 검증 시스템
- **AI 분석** - OpenAI GPT-4o-mini 기반 신고 내용 검증
- **자동 처리** - 일치/불일치/부분일치 판단 후 자동 처리
- **관리자 대시보드** - 신고 내역 관리 및 통계
- **승인/거부** - 부분일치 건에 대한 관리자 최종 판단

## 기술 스택

- **백엔드**: FastAPI 0.115+, Python 3.11+
- **템플릿**: Jinja2 3.1+
- **프론트엔드**: HTML5, CSS3, Vanilla JavaScript
- **HTTP 클라이언트**: httpx 0.24+
- **데이터베이스**: 
  - MySQL (PyMySQL) - 메인 데이터 저장
  - ChromaDB - 벡터 데이터베이스 (Ethics RAG, Agent 검색)
  - Redis 5.0+ - 캐싱
- **AI/ML**: 
  - **Agent**: LangGraph 0.0.20+, LangChain 0.1.0+ (ReAct 패턴)
  - **LLM**: OpenAI GPT-4o-mini (Agent, 분석)
  - **임베딩**: 
    - BGE-M3 (로컬, 한국어, Agent 검색용)
    - OpenAI text-embedding-3-small (Ethics RAG)
  - **NLP**: 
    - PyTorch - BERT 모델
    - Transformers - KcBERT
    - kss (Korean Sentence Splitter) - 한국어 문장 분리
  - **Vision**: OpenAI Vision API (이미지 분석)
  - **NSFW 감지**: nudenet (1차 필터)
- **백그라운드 작업**: APScheduler 3.10+, Threading
- **로깅**: Loguru 0.7+

## 설치 및 실행

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

설치되는 주요 패키지:
- LangGraph, LangChain (AI Agent)
- sentence-transformers, FlagEmbedding (BGE-M3 임베딩)
- chromadb (벡터 데이터베이스)
- nudenet (NSFW 감지)
- kss (한국어 문장 분리)

### 2. 환경 변수 설정

```bash
cp config.env.example config.env
```

`config.env` 파일에 OpenAI API 키를 설정합니다:

```bash
OPENAI_API_KEY=sk-proj-your-actual-openai-api-key-here
```

**OpenAI API 키 발급 방법:**
1. https://platform.openai.com/api-keys 접속
2. "Create new secret key" 클릭하여 API 키 생성
3. 생성된 키를 `config.env` 파일에 입력

**API 키 테스트:**
```bash
python test_api_key.py
```

### 3. Agent 챗봇 설정 (선택)

게시글/댓글 검색 기능을 사용하려면 임베딩을 생성해야 합니다:

```bash
python -m agent_back.embed_board_comments
```

- 최초 실행 시 BGE-M3 모델 다운로드 (약 2GB, 1-2분 소요)
- 게시글과 댓글을 벡터화하여 `chroma_store/` 저장
- 새 게시글 추가 시 재실행하여 업데이트

### 4. 개발 서버 실행

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

### 5. 브라우저에서 접속

- **메인 대시보드**: http://localhost:8000
- **AI Agent Chatbot**: http://localhost:8000/chatbot ⭐
- **게시판**: http://localhost:8000/board
- **API 문서**: http://localhost:8000/docs
- **TrendStream API**: http://localhost:8001/docs
- **TrendStream 대시보드**: http://localhost:8001/public/dad_dashboard.html

## 폴더 구조

```
WMAI/
├── app/                        # 메인 애플리케이션
│   ├── main.py                 # FastAPI 엔트리포인트
│   ├── settings.py             # 환경 설정
│   ├── auth.py                 # 인증/세션 관리
│   ├── api/
│   │   ├── routes_agent.py     # Agent 챗봇 API
│   │   ├── routes_api.py       # 일반 API 엔드포인트
│   │   ├── routes_public.py    # 페이지 라우팅
│   │   ├── routes_board.py     # 게시판 API
│   │   ├── routes_auth.py      # 로그인/회원가입
│   │   └── routes_health.py    # 헬스체크
│   ├── templates/              # Jinja2 템플릿
│   │   ├── base.html
│   │   ├── components/
│   │   └── pages/              # chatbot.html, board_list.html 등
│   └── static/                 # 정적 파일 (CSS, JS, 이미지)
│       └── uploads/board/      # 게시글 이미지 업로드
│
├── agent_back/                 # AI Agent Chatbot ⭐
│   ├── agent_core.py           # LangGraph Agent 코어 (ReAct 패턴)
│   ├── agent_tools.py          # 15개 도구 정의
│   ├── bge_m3_embeddings.py    # BGE-M3 임베딩 모델
│   ├── semantic_chunker.py     # 텍스트 청킹
│   ├── bm25_store.py           # BM25 키워드 검색
│   ├── reranker.py             # 검색 결과 재정렬
│   └── embed_board_comments.py # 게시글/댓글 임베딩 생성
│
├── chroma_store/               # Agent용 벡터 DB
│   ├── chroma.sqlite3          # 게시글/댓글 임베딩
│   └── bm25_index.pkl          # BM25 인덱스
│
├── ethics/                     # Ethics 분석 시스템
│   ├── ethics_hybrid_predictor.py  # 하이브리드 분석기 (BERT + GPT + RAG)
│   ├── ethics_db_logger.py     # 로그 관리 (MySQL)
│   ├── ethics_vector_db.py     # 벡터DB 관리 (ChromaDB)
│   ├── ethics_embedding.py     # 임베딩 생성 (OpenAI API)
│   ├── ethics_text_splitter.py # 텍스트 청킹 (kss 기반)
│   ├── ethics_predict.py       # BERT 예측 모델
│   ├── vision_analyzer.py      # 이미지 분석 (NSFW + Vision API)
│   └── models/                 # ML 모델 설정
│
├── ethics_chroma_store/        # Ethics용 벡터 DB
│   └── chroma.sqlite3          # 고신뢰도 케이스 저장
│
├── chrun_backend/              # 이탈 분석 백엔드 로직
│   ├── chrun_main.py           # FastAPI 라우터
│   ├── chrun_analytics.py      # 분석 엔진
│   ├── chrun_models.py         # 데이터베이스 모델
│   ├── chrun_schemas.py        # API 스키마
│   ├── chrun_database.py       # 데이터베이스 연결
│   └── rag_pipeline/           # 이탈 분석 RAG
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
├── db/                         # 데이터베이스 관리
│   ├── wmai_251114.sql         # 최신 DB 백업 (2024-11-14)
│   ├── migrations_all.sql      # 전체 스키마
│   ├── README.md               # 마이그레이션 가이드
│   └── archive/                # 구 마이그레이션 파일
│
├── match_backend/              # 매칭 시스템
├── requirements.txt            # 통합 의존성 목록
├── run_server.py               # 서버 실행 스크립트
├── AGENT_CHATBOT_GUIDE.md      # Agent 챗봇 가이드
└── README.md
```

## API 엔드포인트

### 메인 애플리케이션 (포트 8000)

#### Agent Chatbot API ⭐
- `POST /api/agent/chat` - Agent와 대화
  - Request: `{"query": "질문", "session_id": "optional"}`
  - Response: `{"answer": "답변", "tool_used": "도구명", "action_type": "view/execute"}`
- `GET /api/agent/health` - Agent 상태 확인
- `DELETE /api/agent/session/{session_id}` - 대화 세션 초기화

#### 게시판 API
- `GET /api/board/list` - 게시글 목록 조회
- `GET /api/board/{post_id}` - 게시글 상세 조회
- `POST /api/board/create` - 게시글 작성 (이미지 첨부 가능)
- `PUT /api/board/{post_id}` - 게시글 수정
- `DELETE /api/board/{post_id}` - 게시글 삭제
- `POST /api/board/{post_id}/comment` - 댓글 작성

#### 검색 & 분석
- `GET /api/search?q={query}` - 자연어 검색
- `GET /api/trends?limit={limit}` - 실시간 트렌드 데이터
- `GET /api/metrics/bounce` - 이탈률 데이터
- `GET /api/reports/moderation` - 신고 분류 데이터

#### Ethics 분석 API
- `POST /api/ethics/analyze` - 비윤리/스팸 분석 (RAG 통합)
  - Request: `{"text": "분석할 텍스트"}`
  - Response: 점수, 신뢰도, RAG 정보, 즉시 차단 여부
- `GET /api/ethics/logs` - 분석 로그 조회 (RAG 상세 포함)
  - Query: `limit`, `offset`, `min_score`, `max_score`, `start_date`, `end_date`
- `GET /api/ethics/logs/stats` - 통계 정보
  - Query: `days` (기본값: 7)
  - Response: 전체 건수, 평균 점수, RAG 적용 건수, 즉시 차단 건수
- `DELETE /api/ethics/logs/{log_id}` - 특정 로그 삭제
- `DELETE /api/ethics/logs/batch/old` - 오래된 로그 삭제
  - Query: `days` (기본값: 90, 0이면 전체 삭제)

### WMAA 신고 검증 API

- `POST /api/analyze` - 신고 내용 AI 분석
- `GET /api/examples` - 신고 예시 데이터
- `GET /api/reports/list` - 신고 목록 조회
- `GET /api/reports/detail/{report_id}` - 특정 신고 상세 조회
- `PUT /api/reports/update/{report_id}` - 신고 상태 업데이트

### 프론트엔드 라우트

- `GET /` - 메인 페이지
- `GET /chatbot` - AI Agent Chatbot 대화 페이지 ⭐
- `GET /board` - 게시판 목록
- `GET /board/{post_id}` - 게시글 상세 페이지
- `GET /board/write` - 게시글 작성 페이지
- `GET /api-console` - API 콘솔
- `GET /churn` - 이탈 분석 대시보드
- `GET /trends` - 트렌드 대시보드
- `GET /reports` - 신고글 검증 (WMAA)
- `GET /reports/admin` - 신고 관리 대시보드
- `GET /ethics_analyze` - 비윤리/스팸지수 평가 (즉시 차단 지원)
- `GET /ethics_dashboard` - Ethics 로그 대시보드 (RAG 통계 포함)
- `GET /login` - 로그인
- `GET /register` - 회원가입
- `GET /health` - 헬스체크

### TrendStream API (포트 8001)

- `GET /v1/trends/popular` - 인기 검색어 조회
- `GET /v1/stats/board` - 게시판 통계
- `POST /v1/ingest/event` - 이벤트 수집
- `GET /v1/analytics/keywords` - 키워드 분석
- `GET /health` - 헬스체크

## 주요 기능 설명

### AI Agent Chatbot (LangGraph 기반) ⭐

WMAI의 핵심 기능인 AI Agent Chatbot은 자연어로 커뮤니티를 관리할 수 있는 지능형 어시스턴트입니다.

#### 아키텍처
- **ReAct 패턴**: Thought → Action → Observation 사이클로 자율 작동
- **15개 도구**: 검색, 분석, 게시판 조작, 신고 관리, 보고서 생성
- **세션 관리**: 대화 기억 기능으로 맥락 유지
- **하이브리드 검색**: BGE-M3 임베딩 + BM25 키워드 검색

#### 주요 도구
1. **semantic_search_tool** - 게시글/댓글 의미 기반 검색
2. **churn_analysis_tool** - 이탈률 조회
3. **ethics_check_tool** - 비윤리/스팸 분석 조회
4. **match_reports_tool** - 신고 통계 조회
5. **trends_analysis_tool** - 트렌드 키워드 조회
6. **execute_churn_analysis_tool** - 이탈 분석 실행
7. **execute_ethics_analysis_tool** - 비윤리 분석 실행
8. **approve_report_tool** - 신고 승인
9. **reject_report_tool** - 신고 거부
10. **filter_reports_tool** - 신고 필터링
11. **board_navigation_tool** - 게시판 정렬/페이지 이동
12. **board_detail_tool** - 게시글 상세보기
13. **board_filter_tool** - 카테고리 필터링
14. **board_page_tool** - 페이지 이동
15. **daily_report_tool** - 일일 보고서 생성

#### 사용 예시
- "육아 관련 글 찾아줘" → semantic_search_tool 자동 실행
- "이탈률 어때?" → churn_analysis_tool 실행 후 `/churn` 이동 버튼 제공
- "비윤리적인 댓글 있어?" → ethics_check_tool 실행 후 통계 표시
- "신고 18번 승인해줘" → approve_report_tool 실행 후 상태 업데이트
- "오늘의 할일 보여줘" → daily_report_tool 실행 후 종합 리포트 생성

자세한 내용은 [AGENT_CHATBOT_GUIDE.md](./AGENT_CHATBOT_GUIDE.md) 참조

### 트렌드 API (MySQL 기반)

`/api/trends` 엔드포인트는 MySQL 데이터베이스에서 트렌드 데이터를 조회합니다:

1. **데이터베이스 조회** - `trend_keywords` 테이블에서 최근 7일간 데이터 조회
2. **날짜별 집계** - 타임라인 데이터 생성
3. **증감률 계산** - 전일 대비 트렌드 변화 분석
4. **Fallback** - MySQL 오류 시 더미 데이터 반환

**설정 방법:**
```bash
# 최신 DB 스키마 적용 (권장)
mysql -u root -p wmai < db/wmai_251114.sql

# 또는 개별 마이그레이션 실행
mysql -u root -p wmai < db/migrations_all.sql
```

자세한 내용은 `db/README.md` 참조

### Ethics 분석 시스템 (고도화)

하이브리드 + RAG 방식으로 텍스트의 비윤리성과 스팸 여부를 분석:

#### 1. 다층 분석 파이프라인
1. **BERT 모델** - 한국어 텍스트 비윤리 점수 예측
2. **규칙 기반 스팸 감지** - 키워드, 패턴, 반복 감지
3. **욕설 감지** - 사전 정의된 패턴 매칭 (부스트 점수 적용)
4. **GPT-4.1-nano** - 종합적인 비윤리/스팸 판단
5. **RAG 시스템** - 유사 사례 검색 및 점수 보정

#### 2. RAG (Retrieval-Augmented Generation) 시스템
- **문장 분리**: kss(Korean Sentence Splitter)를 사용한 정교한 한국어 문장 분리
  - 종결 어미 인식 (다, 요, 임 등)
  - 따옴표, 괄호 자동 처리
  - 줄임표, 특수 문장부호 지원
  - 폴백 메커니즘 (kss 미설치 시 정규식 사용)
- **벡터 검색**: 문장별 임베딩 생성 (OpenAI text-embedding-3-small)
- **유사 사례 검색**: ChromaDB에서 신뢰도 80% 이상 사례 검색
- **관리자 확정 우선**: 관리자가 확정한 사례에 더 높은 가중치 부여
- **점수 보정 가중치**:
  - 유사도 ≥80% & 확정 케이스 ≥1개 → 60% 가중치
  - 유사도 ≥80% & 케이스 ≥2개 → 50% 가중치
  - 유사도 ≥80% & 케이스 ≥1개 → 30% 가중치
  - 유사도 70~80% & 확정 케이스 ≥1개 → 40% 가중치

#### 3. 즉시 차단 (LLM 건너뛰기)
- **조건**: 유사도 ≥90%, 점수 ≥90, 신뢰도 ≥80% 확정 사례 발견
- **효과**: LLM 분석 건너뛰고 즉시 차단 (비용 절감, 속도 향상)
- **점수**: `null` 반환 (BERT 단독 신뢰도 낮음)

#### 4. 성능 최적화
- **배치 임베딩**: 한 번의 OpenAI API 호출로 여러 문장 처리 (4-6배 속도 향상)
- **비동기 저장**: 벡터DB 저장을 백그라운드로 처리 (1-5초 응답 단축)
- **병렬 처리**: 여러 문장 임베딩을 동시 생성

#### 5. 데이터 저장
- **MySQL**: `ethics_logs` (기본 분석 로그), `ethics_rag_logs` (RAG 상세 정보)
- **ChromaDB**: 고신뢰도 케이스 벡터 저장 (신뢰도 ≥80%)
- **자동 저장**: 분석 후 자동으로 고신뢰도 케이스 저장 (비동기)

## 개발 가이드

### 코드 규칙

1. API 엔드포인트 추가 시 `routes_api.py`에 작성
2. 페이지 라우트 추가 시 `routes_public.py`에 작성
3. 공용 스타일은 `app/static/css/app.css`에 추가
4. JavaScript는 `app/static/js/app.js`에 공통 함수 작성
5. 템플릿은 `base.html`을 상속하여 작성

### Agent Chatbot 사용 가이드

#### 접근 방법
1. 홈페이지(`/`)에서 검색창에 질문 입력 → 자동으로 챗봇 페이지 이동
2. 또는 "🤖 AI 챗봇" 카드 클릭
3. 또는 `/chatbot` 직접 접속

#### 사용 예시
- **게시글 검색**: "육아에 대한 글 찾아줘", "다이어트 관련 댓글 보여줘"
- **분석 조회**: "이탈률 어때?", "비윤리적인 댓글 있어?", "트렌드 키워드 알려줘"
- **게시판 조작**: "자유게시판만 보여줘", "인기순으로 정렬해줘", "다음 페이지"
- **상세보기**: "첫 번째 글 자세히 보여줘", "게시글 5번 상세보기"
- **신고 관리**: "신고 18번 승인해줘", "대기중 신고 보여줘"
- **보고서**: "오늘의 할일 보여줘", "일일 보고서 생성"

자세한 내용은 [AGENT_CHATBOT_GUIDE.md](./AGENT_CHATBOT_GUIDE.md) 참조

### API 통합

JavaScript에서 API 호출:

```javascript
// 일반 API 호출
const data = await apiRequest('/api/trends?limit=50');
console.log(data.keywords);

// Agent 챗봇 API 호출
const response = await fetch('/api/agent/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ query: "육아 관련 글 찾아줘" })
});
const result = await response.json();
console.log(result.answer);
```

### 이탈 분석 대시보드 통합

#### 접근 방법
1. 홈페이지(`/`) 접속
2. "이탈 분석 대시보드" 카드 클릭
3. 이탈 분석 대시보드(`/churn`) 페이지로 이동
4. 또는 챗봇에서 "이탈률 알려줘" 입력 → 자동 이동 버튼 제공

#### 사용 흐름
1. CSV 파일 업로드 (user_hash, created_at, action, gender, age_band, channel 컬럼 필요)
2. 분석 기간 설정 (시작일, 종료일)
3. 세그먼트 선택 (성별, 연령대, 채널)
4. "분석 실행" 버튼 클릭
5. 이탈률, 활성 사용자 수, 장기 미접속 사용자 등 지표 확인
6. 차트를 통한 시각적 분석 결과 확인
7. RAG 기반 유사 패턴 분석 및 인사이트 제공

### 게시판 사용 가이드

#### 게시글 작성
1. 로그인 후 `/board` 접속
2. "글쓰기" 버튼 클릭
3. 제목, 내용, 카테고리 선택
4. 이미지 첨부 (선택, 최대 5개, 5MB 제한)
5. "작성" 버튼 클릭
6. 자동 비윤리/스팸 분석 (텍스트 + 이미지)
7. 문제 없으면 게시, 문제 있으면 차단

#### 이미지 분석
- **1차 필터**: NSFW 감지 (nudenet, 로컬)
- **2차 검증**: Vision API 분석 (OpenAI GPT-4o-mini)
- **비용 최적화**: reasoning 제외로 50% 절감
- **로그 저장**: `image_analysis_logs` 테이블
- **대시보드**: `/ethics_dashboard`에서 이미지 분석 이력 확인

### Ethics 분석 사용 예시

#### Python API 사용
```python
from ethics.ethics_hybrid_predictor import HybridEthicsAnalyzer

analyzer = HybridEthicsAnalyzer()
result = analyzer.analyze("분석할 텍스트")

# 기본 정보
print(f"비윤리 점수: {result['final_score']}")
print(f"스팸 점수: {result['spam_score']}")
print(f"신뢰도: {result['final_confidence']}")

# RAG 정보
if result.get('adjustment_applied'):
    print(f"RAG 보정 적용됨")
    print(f"유사 사례 수: {result['similar_cases_count']}")
    print(f"최대 유사도: {result['max_similarity'] * 100:.1f}%")

# 즉시 차단 여부
if result.get('auto_blocked'):
    print(f"즉시 차단됨 (LLM 분석 건너뛰기)")
    print(f"사유: {result['auto_block_reason']}")
```

#### REST API 사용
```bash
curl -X POST "http://localhost:8000/api/ethics/analyze" \
  -H "Content-Type: application/json" \
  -d '{"text": "분석할 텍스트"}'
```

#### 응답 예시
```json
{
  "text": "분석할 텍스트",
  "score": 85.3,
  "confidence": 92.1,
  "spam": 15.2,
  "spam_confidence": 78.5,
  "types": ["욕설 및 비방"],
  "auto_blocked": false,
  "detailed": {
    "bert_score": 79.1,
    "llm_score": 88.5,
    "rag": {
      "enabled": true,
      "adjustment_applied": true,
      "similar_cases_count": 3,
      "max_similarity": 0.87,
      "adjustment_weight": 0.5
    }
  }
}
```

#### 즉시 차단 응답 예시
```json
{
  "text": "차단될 텍스트",
  "score": null,
  "confidence": null,
  "spam": null,
  "spam_confidence": null,
  "types": ["욕설 및 비방"],
  "auto_blocked": true,
  "detailed": {
    "bert_score": 79.1,
    "llm_score": null,
    "rag": {
      "enabled": true,
      "similar_cases_count": 1,
      "max_similarity": 0.94
    }
  }
}
```

## 성능 최적화

### Ethics 분석 성능 개선 (2025년 1월 업데이트)

#### 배치 임베딩 처리
- **개선 전**: 5문장 분석 시 5번 API 호출 (4초)
- **개선 후**: 5문장 분석 시 1번 API 호출 (0.8초)
- **효과**: **4-6배 속도 향상** ⚡

#### 비동기 벡터DB 저장
- **개선 전**: 분석 → 저장 대기 (1-5초) → 응답
- **개선 후**: 분석 → 즉시 응답 (저장은 백그라운드)
- **효과**: **사용자 응답 시간 1-5초 단축** ⚡

#### 전체 성능 개선 효과
| 텍스트 길이 | 개선 전 | 개선 후 | 향상률 |
|------------|---------|---------|--------|
| 짧은 텍스트 (2문장) | 3-5초 | 1-2초 | 2-3배 |
| 중간 텍스트 (5문장) | 6-10초 | 2-3초 | 3-4배 |
| 긴 텍스트 (10문장) | 10-15초 | 3-5초 | 3-5배 |

#### 즉시 차단 시스템
- **조건**: 유사도 90% 이상 확정 사례 발견
- **효과**: LLM 분석 건너뛰기 → **비용 절감 + 속도 향상**
- **정확도**: 관리자 확정 사례 기반 → **높은 신뢰도**

## 배포

### Docker Compose (TrendStream)

```bash
cd trend
docker-compose up -d
```

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
5. 챗봇 통합: "신고 18번 승인해줘" 입력으로 자동 처리 가능

### 신고 관리 대시보드 (`/reports/admin`)

1. **대시보드 탭**: 신고 통계 및 처리 현황 확인
2. **신고 목록 탭**: 
   - 모든 신고 내역 조회
   - 필터링: 상태별, 유형별, 기간별
   - 부분일치 신고에 대한 승인/반려 처리
3. **통계 분석 탭**: 월별 트렌드 및 처리 시간 분석
4. **챗봇 연동**: "대기중 신고 보여줘" 입력으로 필터링 가능

### 데이터 저장

신고 데이터는 `match_reports_db.json` 파일에 저장됩니다. 이 파일은 `.gitignore`에 포함되어 있어 Git에 커밋되지 않습니다.

## 통합 가이드 문서

- **[AGENT_CHATBOT_GUIDE.md](./AGENT_CHATBOT_GUIDE.md)** - AI Agent Chatbot 상세 가이드
- **[IMAGE_ANALYSIS_DASHBOARD_GUIDE.md](./IMAGE_ANALYSIS_DASHBOARD_GUIDE.md)** - 이미지 분석 대시보드 가이드
- **[db/README.md](./db/README.md)** - 데이터베이스 마이그레이션 가이드
- **[ENVIRONMENT_SETUP.md](./ENVIRONMENT_SETUP.md)** - 환경 설정 가이드
- **[OPENAI_SETUP_GUIDE.md](./OPENAI_SETUP_GUIDE.md)** - OpenAI API 설정 가이드

## 라이선스

MIT License

## 기여

프로젝트에 기여하시려면 Pull Request를 생성해주세요.

## 주요 업데이트 내역

### 2024년 11월 14일 - AI Agent Chatbot & 이미지 분석 통합 ⭐
- ✅ **AI Agent Chatbot**: LangGraph 기반 자율 에이전트 구현
  - ReAct 패턴으로 15개 도구 자동 선택
  - BGE-M3 임베딩 (로컬, 무료, 한국어 최적화)
  - 게시판 조작, 분석 자동화, 일일 보고서 생성
- ✅ **이미지 분석**: NSFW 감지 + Vision API 2차 검증
  - Vision API 비용 50% 절감 (reasoning 제외)
  - 게시글당 최대 5개 이미지 업로드
  - 이미지 분석 로그 대시보드
- ✅ **게시판 시스템**: 커뮤니티 게시판 구현
  - 게시글/댓글 작성, 수정, 삭제
  - 카테고리 분류 (자유/질문/정보)
  - 실시간 검색 및 필터링
- ✅ **인증 시스템**: 로그인/회원가입 구현
- ✅ **DB 마이그레이션**: `db/archive/` 폴더 정리

### 2025년 1월 - Ethics 분석 시스템 고도화
- ✅ **RAG 시스템 통합**: ChromaDB 벡터 데이터베이스 활용
- ✅ **kss 문장 분리**: 한국어 특화 문장 분리기 적용
- ✅ **즉시 차단 기능**: 고신뢰도 확정 사례와 유사 시 LLM 건너뛰기
- ✅ **배치 임베딩**: OpenAI API 호출 최적화 (4-6배 속도 향상)
- ✅ **비동기 저장**: 벡터DB 저장 백그라운드 처리 (1-5초 단축)
- ✅ **RAG 로그**: `ethics_rag_logs` 테이블 추가
- ✅ **대시보드 개선**: RAG 통계, 즉시 차단 건수 표시

### 2024년 12월 - 초기 구축
- 🎉 WMAA 신고 검증 시스템 통합
- 🎉 TrendStream 백엔드 통합
- 🎉 이탈 분석 대시보드 통합
- 🎉 Ethics 분석 기본 시스템 구축

## 문의

프로젝트 관련 문의사항이 있으시면 이슈를 등록해주세요.

