"""커뮤니티 관련 API 라우트"""
from fastapi import APIRouter

router = APIRouter(
    prefix="/api/v1/community",
    tags=["Community"]
)


@router.get("/")
async def get_community_trends():
    """커뮤니티 트렌드 조회 (추후 구현)"""
    return {
        "message": "Community trends endpoint - Coming soon",
        "data": []
    }

