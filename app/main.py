"""
🚀 FastAPI 메인 서버
시니어의 코딩 원칙:
1. 명확한 주석
2. 에러 처리
3. 로깅
4. 환경 변수 사용
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os
from pathlib import Path

# FastAPI 앱 생성
app = FastAPI(
    title="Community Admin Frontend",
    description="커뮤니티 관리자용 API 서비스 프론트엔드",
    version="1.0.0",
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc"  # ReDoc
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
    from app.api import routes_public, routes_health, routes_api
    app.include_router(routes_public.router)
    app.include_router(routes_health.router)
    app.include_router(routes_api.router, prefix="/api")
    print("[OK] 라우터 등록 완료")
except ImportError as e:
    print(f"[WARN] 라우터 임포트 실패: {e}")
    # 기본 라우트만 제공
    pass

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
    print("="*50 + "\n")

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

