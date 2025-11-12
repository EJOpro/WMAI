"""
FastAPI 메인 서버
시니어의 코딩 원칙:
1. 명확한 주석
2. 에러 처리
3. 로깅
4. 환경 변수 사용
"""

import sys
import io
import logging

# Windows에서 UTF-8 출력 설정
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', line_buffering=True)

# 로깅 설정 (중요한 로그만 출력)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    force=True  # 기존 설정 덮어쓰기
)

# 불필요한 로그 레벨 조정 (WARNING 이상만 출력)
logging.getLogger('httpx').setLevel(logging.WARNING)  # HTTP 요청 로그 숨김
logging.getLogger('chrun_backend.rag_pipeline').setLevel(logging.INFO)  # DEBUG → INFO
logging.getLogger('chrun_backend.rag_pipeline.embedding_service').setLevel(logging.WARNING)  # 임베딩 생성 로그 숨김
logging.getLogger('chrun_backend.rag_pipeline.vector_db').setLevel(logging.WARNING)  # 벡터DB 검색 로그 숨김
logging.getLogger('chrun_backend.rag_pipeline.rag_checker').setLevel(logging.INFO)
logging.getLogger('chrun_backend.rag_pipeline.rag_decider').setLevel(logging.INFO)

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
import os
from pathlib import Path
from dotenv import load_dotenv
import secrets

# 환경 변수 로드 (match_config.env 파일)
load_dotenv('match_config.env')

# FastAPI 앱 생성
app = FastAPI(
    title="Community Admin Frontend",
    description="커뮤니티 관리자용 API 서비스 프론트엔드",
    version="1.0.0",
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc"  # ReDoc
)

# 세션 미들웨어 추가 (인증에 필요)
SESSION_SECRET_KEY = os.getenv('SESSION_SECRET_KEY', secrets.token_urlsafe(32))
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET_KEY,
    session_cookie="wmai_session",
    max_age=86400,  # 24시간
    same_site="lax",
    https_only=False  # 개발 환경에서는 False, 프로덕션에서는 True
)

# CORS 설정 (프론트엔드 개발용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 디렉토리 확인 및 생성
STATIC_DIR = Path("app/static")
if not STATIC_DIR.exists():
    print(f"[INFO] {STATIC_DIR} 디렉토리가 없습니다. 생성합니다...")
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    (STATIC_DIR / "css").mkdir(exist_ok=True)
    (STATIC_DIR / "js").mkdir(exist_ok=True)
    (STATIC_DIR / "img").mkdir(exist_ok=True)

# 정적 파일 마운트
try:
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    print("[OK] 정적 파일 디렉토리 마운트 완료")
except Exception as e:
    print(f"[WARN] 정적 파일 마운트 실패: {e}")

# 라우터 등록
try:
    from app.api import routes_public, routes_health, routes_api, routes_match, routes_auth, routes_board, routes_admin, routes_agent
    app.include_router(routes_public.router)
    app.include_router(routes_health.router)
    app.include_router(routes_api.router, prefix="/api")
    app.include_router(routes_match.router, prefix="/api")  # WMAA 신고 검증 API
    app.include_router(routes_auth.router, prefix="/api")  # 인증 API
    app.include_router(routes_board.router, prefix="/api")  # 게시판 API
    app.include_router(routes_admin.router, prefix="/api")  # 관리자 API
    app.include_router(routes_agent.router, prefix="/api")  # Agent Chatbot API
    print("[OK] 모든 라우터 등록 완료 (WMAA, Auth, Board, Admin, Agent 포함)")
except ImportError as e:
    print(f"[WARN] 라우터 임포트 실패: {e}")
    # 기본 라우트만 제공
    pass

# 이탈 분석 대시보드 라우터 등록
try:
    from chrun_backend.chrun_main import router as churn_router
    from chrun_backend.chrun_database import init_db
    
    # 데이터베이스 초기화
    init_db()
    print("[OK] 데이터베이스 초기화 완료")
    
    app.include_router(
        churn_router,
        prefix="/api/churn",
        tags=["churn-analysis"]
    )
    print("[OK] 이탈 분석 라우터 등록 완료")
except ImportError as e:
    print(f"[WARN] 이탈 분석 라우터 임포트 실패: {e}")
except Exception as e:
    print(f"[ERROR] 데이터베이스 초기화 실패: {e}")

# 루트 경로 (메인 페이지)
@app.get("/", response_class=HTMLResponse)
async def root():
    """메인 페이지 - index_main.html 반환"""
    html_file = Path("index_main.html")
    if html_file.exists():
        return FileResponse("index_main.html")
    
    # 파일이 없으면 간단한 웰컴 페이지
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Community Admin</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            .container {
                text-align: center;
                background: rgba(255,255,255,0.1);
                padding: 40px;
                border-radius: 20px;
                backdrop-filter: blur(10px);
            }
            h1 { margin: 0 0 20px 0; }
            a {
                color: white;
                text-decoration: none;
                background: rgba(255,255,255,0.2);
                padding: 10px 20px;
                border-radius: 5px;
                display: inline-block;
                margin: 5px;
            }
            a:hover { background: rgba(255,255,255,0.3); }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>FastAPI Server Running!</h1>
            <p>Community Admin Dashboard</p>
            <div style="margin-top: 20px;">
                <a href="/docs">API Documentation</a>
                <a href="/health">Health Check</a>
                <a href="/test.html">Test Page</a>
            </div>
        </div>
    </body>
    </html>
    """

# 시작 이벤트
@app.on_event("startup")
async def startup_event():
    print("\n" + "="*50)
    print("Community Admin FastAPI Server Started!")
    print("="*50)
    print("Server: http://localhost:8000")
    print("API Docs: http://localhost:8000/docs")
    print("Health: http://localhost:8000/health")
    print("WMAA Reports: http://localhost:8000/reports")
    print("WMAA Admin: http://localhost:8000/reports/admin")
    
    # API 키 상태 확인
    api_key = os.getenv('OPENAI_API_KEY', '')
    if api_key and api_key != 'your-api-key-here':
        print(f"✅ OpenAI API Key: {api_key[:10]}...{api_key[-4:]} (로드됨)")
    else:
        print("❌ OpenAI API Key: 설정되지 않음 (match_config.env 파일 확인 필요)")
    
    print("="*50 + "\n")
    
    # Ethics 분석기 초기화 (서버 시작 시)
    print("[INFO] Ethics 분석기 초기화 중...")
    try:
        from ethics.ethics_hybrid_predictor import HybridEthicsAnalyzer
        from app.api import routes_api
        routes_api.ethics_analyzer = HybridEthicsAnalyzer()
        print("[OK] Ethics 분석기 초기화 완료")
    except Exception as e:
        print(f"[WARN] Ethics 분석기 초기화 실패: {e}")
        print("       첫 API 호출 시 재시도됩니다.")

# 종료 이벤트
@app.on_event("shutdown")
async def shutdown_event():
    print("\nServer shutting down...")

# 직접 실행 시
if __name__ == "__main__":
    import uvicorn
    print("\nStarting development server...")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

