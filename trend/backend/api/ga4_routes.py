"""Google Analytics 4 관련 API 라우트"""
from fastapi import APIRouter

router = APIRouter(
    prefix="/api/v1/ga4",
    tags=["GA4"]
)


@router.get("/")
async def get_ga4_data():
    """GA4 데이터 조회 (추후 구현)"""
    return {
        "message": "GA4 data endpoint - Coming soon",
        "data": []
    }

