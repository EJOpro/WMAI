"""TrendStream FastAPI 메인 애플리케이션"""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from loguru import logger
import sys
import time

from backend.api import ingest_routes, trends_routes, community_routes, ga4_routes, stats_routes, popular_routes, analytics_routes
from backend.workers.aggregator import aggregation_worker
from backend.services.database import test_connection
from backend.services.cache import cache_service
from config.settings import settings

# 로깅 설정
logger.remove()
logger.add(
    sys.stdout,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    level=settings.LOG_LEVEL
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    # 시작 시
    logger.info("Starting TrendStream API...")
    
    # DB 연결 테스트 (선택적)
    try:
        if not test_connection():
            logger.warning("Database connection failed! Some features will be disabled.")
    except Exception as e:
        logger.warning(f"Database connection test failed: {e}")
    
    # Redis 연결 테스트 (선택적)
    try:
        if not cache_service.ping():
            logger.warning("Redis connection failed! Cache will be disabled.")
    except Exception as e:
        logger.warning(f"Redis connection test failed: {e}")
    
    # 집계 워커 시작 (선택적) - 비활성화됨 (성능 문제로)
    # try:
    #     aggregation_worker.start()
    # except Exception as e:
    #     logger.warning(f"Aggregation worker failed to start: {e}")
    logger.info("Aggregation worker is DISABLED for performance")
    
    logger.info("TrendStream API started successfully")
    
    yield
    
    # 종료 시
    logger.info("Shutting down TrendStream API...")
    # try:
    #     aggregation_worker.stop()
    # except Exception as e:
    #     logger.warning(f"Error stopping aggregation worker: {e}")
    logger.info("TrendStream API stopped")


# FastAPI 앱 생성
app = FastAPI(
    title="TrendStream API",
    description="웹 트래픽 수집·집계·분석 REST API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=f"/{settings.API_VERSION}/docs",
    redoc_url=f"/{settings.API_VERSION}/redoc",
    openapi_url=f"/{settings.API_VERSION}/openapi.json"
)

# 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 origin 허용 (개발 환경)
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],  # 모든 헤더 허용
    expose_headers=["*"],  # 모든 응답 헤더 노출
    max_age=3600,  # preflight 캐시 1시간
)

app.add_middleware(GZipMiddleware, minimum_size=1000)


# 요청 로깅 미들웨어
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """모든 요청 로깅"""
    start_time = time.time()
    
    # 요청 처리
    response = await call_next(request)
    
    # 처리 시간 계산
    process_time = (time.time() - start_time) * 1000
    
    # 로그 출력
    logger.info(
        f"{request.method} {request.url.path} "
        f"status={response.status_code} "
        f"duration={process_time:.2f}ms"
    )
    
    # 응답 헤더에 처리 시간 추가
    response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
    
    return response


# OPTIONS 요청은 CORS 미들웨어가 자동 처리
# 수동 OPTIONS 핸들러는 라우터와 충돌하여 405 에러 발생 가능
# @app.options("/{path:path}")
# async def options_handler(path: str):
#     """모든 OPTIONS 요청 처리"""
#     return JSONResponse(
#         status_code=200,
#         content={"message": "OK"},
#         headers={
#             "Access-Control-Allow-Origin": "*",
#             "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
#             "Access-Control-Allow-Headers": "Accept, Accept-Language, Content-Language, Content-Type, Authorization, X-Requested-With, X-Custom-Header, gtm-event-type",
#             "Access-Control-Allow-Credentials": "true"
#         }
#     )

# 전역 예외 핸들러
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """전역 예외 처리"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.LOG_LEVEL == "DEBUG" else "An unexpected error occurred"
        }
    )


# 정적 파일 서빙
app.mount("/public", StaticFiles(directory="public"), name="public")

# 라우터 등록
app.include_router(ingest_routes.router, prefix="")
app.include_router(trends_routes.router, prefix="")
app.include_router(community_routes.router, prefix="")
app.include_router(ga4_routes.router, prefix="")
app.include_router(stats_routes.router, prefix="")
app.include_router(popular_routes.router, prefix="")
app.include_router(analytics_routes.router, prefix="")


# 헬스체크 엔드포인트
@app.get("/health", tags=["Health"])
async def health_check():
    """헬스체크"""
    try:
        db_ok = test_connection()
    except:
        db_ok = False
    
    try:
        redis_ok = cache_service.ping()
    except:
        redis_ok = False
    
    return {
        "status": "healthy" if db_ok and redis_ok else "degraded",
        "database": "ok" if db_ok else "error",
        "cache": "ok" if redis_ok else "error",
        "version": "1.0.0"
    }


@app.get("/", tags=["Root"])
async def root():
    """루트 엔드포인트"""
    return {
        "service": "TrendStream API",
        "version": "1.0.0",
        "docs": f"/{settings.API_VERSION}/docs",
        "dashboards": {
            "dad": "/public/dad_dashboard.html",
            "ga4": "/public/ga4_dashboard.html",
            "keyword": "/public/keyword_analysis_dashboard.html"
        }
    }


@app.get("/dashboard/", tags=["Dashboard"])
async def dashboard_redirect():
    """대시보드 리다이렉트"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/public/dad_dashboard.html")


@app.get("/favicon.ico", tags=["Static"])
async def favicon():
    """Favicon 404 방지"""
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=204, content={})

@app.get("/popular/test", tags=["Popular"])
async def test_popular():
    """인기검색어 API 테스트"""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("https://dad.dothome.co.kr/adm/popular_api.php?limit=5")
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": "인기검색어 API 연결 성공",
                    "status_code": response.status_code,
                    "content_length": len(response.content)
                }
            else:
                return {
                    "success": False,
                    "message": f"API 오류: {response.status_code}",
                    "status_code": response.status_code
                }
    except Exception as e:
        return {
            "success": False,
            "message": f"연결 실패: {str(e)}"
        }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )

