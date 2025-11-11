# Agent Chatbot 사용 가이드

## 📋 개요

LangGraph 기반 AI Agent Chatbot이 성공적으로 통합되었습니다!
게시글과 댓글을 검색하고, 커뮤니티 관리 기능을 자동으로 수행합니다.

## 🚀 설치 및 실행

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

설치되는 주요 패키지:
- `langchain>=0.1.0` - LangChain 프레임워크
- `langgraph>=0.0.20` - ReAct Agent 구현
- `sentence-transformers>=2.3.0` - 임베딩 모델
- `FlagEmbedding>=1.2.0` - BGE-M3 모델
- `chromadb>=0.4.24` - 벡터 데이터베이스

### 2. 환경 변수 설정

`config.env` 또는 `match_config.env` 파일에 OpenAI API 키 설정:

```env
OPENAI_API_KEY=your-openai-api-key-here
```

### 3. 게시글/댓글 임베딩 생성

데이터베이스에 게시글과 댓글이 있어야 합니다.

```bash
python embed_board_comments.py
```

실행 과정:
1. DB에서 `status='exposed'` 게시글과 댓글 조회
2. BGE-M3 모델로 임베딩 생성 (최초 실행 시 모델 다운로드 약 2GB)
3. ChromaDB에 저장 (`chroma_store/` 디렉토리)

### 4. 서버 실행

```bash
python run_server.py
```

또는

```bash
uvicorn app.main:app --reload --port 8000
```

## 🎯 사용 방법

### 방법 1: 홈 화면에서 검색

1. 브라우저에서 `http://localhost:8000` 접속
2. 검색창에 질문 입력
3. Enter 키 또는 "검색" 버튼 클릭
4. 자동으로 챗봇 페이지로 이동하여 답변 표시

### 방법 2: AI 챗봇 카드 클릭

1. 홈 화면에서 "🤖 AI 챗봇" 카드 클릭
2. 챗봇 페이지에서 대화형으로 질문

### 방법 3: 직접 접속

`http://localhost:8000/chatbot` 직접 접속

## 🛠️ Agent 도구 (5개)

Agent가 자동으로 질문을 분석하여 적절한 도구를 선택합니다:

### 1. 의미 기반 검색 (semantic_search_tool)
- **사용 시기**: 게시글이나 댓글을 검색할 때
- **예시 질문**:
  - "육아에 대한 게시글 찾아줘"
  - "요리 레시피 관련 댓글 보여줘"
  - "다이어트 관련 글 검색해줘"

### 2. 이탈 분석 (churn_analysis_tool)
- **사용 시기**: 사용자 이탈률을 확인할 때
- **예시 질문**:
  - "요즘 이탈률이 어때?"
  - "사용자 이탈 분석 보여줘"
  - "이탈 위험이 있는 사용자는?"
- **페이지 이동**: `/churn`

### 3. 비윤리/스팸 분석 (ethics_check_tool)
- **사용 시기**: 비윤리적 콘텐츠나 스팸을 확인할 때
- **예시 질문**:
  - "비윤리적인 댓글 있어?"
  - "스팸 게시글 얼마나 있어?"
  - "욕설이 포함된 글 찾아줘"
- **페이지 이동**: `/ethics_dashboard`

### 4. 신고 통계 (match_reports_tool)
- **사용 시기**: 신고 현황을 확인할 때
- **예시 질문**:
  - "신고가 많은 게시글 보여줘"
  - "신고 통계 알려줘"
  - "어떤 유형의 신고가 많아?"
- **페이지 이동**: `/reports`

### 5. 트렌드 분석 (trends_analysis_tool)
- **사용 시기**: 인기 키워드나 트렌드를 확인할 때
- **예시 질문**:
  - "트렌드 키워드 알려줘"
  - "요즘 인기 있는 주제는?"
  - "어떤 카테고리가 인기 있어?"
- **페이지 이동**: `/trends`

## 🔧 API 엔드포인트

### POST `/api/agent/chat`
Agent와 대화

**요청:**
```json
{
  "query": "육아에 대한 게시글 찾아줘",
  "session_id": "optional-session-id"
}
```

**응답:**
```json
{
  "answer": "Agent의 답변 내용",
  "tool_used": "의미 기반 검색",
  "page_url": "/churn",
  "session_id": "session-id"
}
```

### GET `/api/agent/health`
Agent 상태 확인

**응답:**
```json
{
  "status": "ok",
  "agent": "LangGraph Community Agent",
  "tools": ["semantic_search", "churn_analysis", "ethics_check", "match_reports", "trends_analysis"],
  "sessions": 2
}
```

### DELETE `/api/agent/session/{session_id}`
대화 세션 초기화

## 📁 파일 구조

```
project/
├── agent_back/
│   ├── __init__.py
│   ├── agent_core.py          # LangGraph Agent 코어
│   ├── agent_tools.py          # 5개 도구 정의
│   └── bge_m3_embeddings.py    # BGE-M3 임베딩 모델
├── app/
│   ├── api/
│   │   ├── routes_agent.py     # Agent API 라우터
│   │   └── routes_public.py    # 챗봇 페이지 라우트
│   ├── templates/
│   │   └── pages/
│   │       ├── home.html       # 홈 화면 (챗봇으로 이동)
│   │       └── chatbot.html    # 챗봇 대화 페이지
│   └── main.py                 # FastAPI 메인 (Agent 라우터 등록)
├── chroma_store/               # 벡터 DB 저장소
│   └── board_comments/         # 게시글/댓글 임베딩
├── embed_board_comments.py     # 임베딩 생성 스크립트
└── requirements.txt            # 의존성 (LangChain, LangGraph 포함)
```

## 🔍 동작 원리

1. **사용자 질문 입력**: 홈 화면 또는 챗봇 페이지에서 질문 입력
2. **Agent 분석**: LangGraph Agent가 질문을 분석하여 적절한 도구 선택
3. **도구 실행**: 
   - semantic_search_tool → ChromaDB에서 게시글/댓글 검색
   - churn_analysis_tool → CSV 데이터 분석
   - ethics_check_tool → DB에서 비윤리 로그 조회
   - match_reports_tool → DB에서 신고 통계 조회
   - trends_analysis_tool → DB에서 카테고리 통계 조회
4. **답변 생성**: GPT-4o가 도구 실행 결과를 자연어로 변환
5. **페이지 이동**: 필요 시 상세 페이지로 이동 버튼 제공

## ⚙️ 기술 스택

- **Agent 프레임워크**: LangGraph (ReAct 패턴)
- **LLM**: OpenAI GPT-4o
- **임베딩**: BGE-M3 (로컬, 무료, 한국어 지원)
- **벡터 DB**: ChromaDB
- **백엔드**: FastAPI
- **프론트엔드**: HTML + Vanilla JavaScript

## 🐛 문제 해결

### 1. OpenAI API 키 오류
```
ValueError: OpenAI API 키가 필요합니다
```
**해결**: `config.env` 파일에 `OPENAI_API_KEY` 설정

### 2. ChromaDB 경로 오류
```
chroma_store를 찾을 수 없습니다
```
**해결**: `python embed_board_comments.py` 실행하여 벡터 DB 생성

### 3. BGE-M3 모델 다운로드
```
BGE-M3 모델 다운로드 중...
```
**참고**: 최초 실행 시 약 2GB 모델 자동 다운로드 (1~2분 소요)

### 4. Import 오류
```
ModuleNotFoundError: No module named 'langgraph'
```
**해결**: `pip install -r requirements.txt` 재실행

### 5. 게시글이 검색되지 않음
- DB에 `status='exposed'` 게시글/댓글이 있는지 확인
- `python embed_board_comments.py` 재실행하여 임베딩 업데이트

## 📊 성능 최적화

- **임베딩 캐싱**: BGE-M3 모델은 싱글톤 패턴으로 한 번만 로드
- **세션 관리**: 대화 기억 기능으로 맥락 유지
- **벡터 DB**: ChromaDB로 빠른 유사도 검색

## 🎉 완료!

Agent Chatbot이 성공적으로 통합되었습니다!
질문을 입력하면 Agent가 자동으로 분석하고 답변합니다. 🚀

