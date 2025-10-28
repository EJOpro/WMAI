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

# Windows에서 UTF-8 출력 설정
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', line_buffering=True)

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

# 라우터 등록 (정적 파일보다 먼저 등록)
try:
    from app.api import routes_public, routes_health, routes_api
    app.include_router(routes_public.router)
    app.include_router(routes_health.router)
    app.include_router(routes_api.router, prefix="/api")
    print("[OK] 라우터 등록 완료")
except ImportError as e:
    print(f"[WARN] 라우터 임포트 실패: {e}")

# 정적 파일 마운트 (라우터보다 나중에 마운트하여 라우트 우선순위 확보)
try:
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    print("[OK] 정적 파일 디렉토리 마운트 완료")
except Exception as e:
    print(f"[WARN] 정적 파일 마운트 실패: {e}")

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

