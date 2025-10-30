"""간단한 Analytics API 라우터 - 외부 사이트용"""
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timedelta
from typing import Optional
from loguru import logger

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/{site_id}")
async def get_site_analytics(
    site_id: str,
    period: str = Query("1h", description="기간: 1h, 24h, 7d, 30d")
):
    """
    사이트별 분석 데이터 조회
    
    간단한 분석 데이터를 반환합니다.
    DB 연결 없이 기본 응답을 제공합니다.
    """
    try:
        logger.info(f"Analytics request: site={site_id}, period={period}")
        
        # 기간 파싱
        now = datetime.now()
        if period == "1h":
            start_time = now - timedelta(hours=1)
            interval = "minute"
        elif period == "24h":
            start_time = now - timedelta(hours=24)
            interval = "hour"
        elif period == "7d":
            start_time = now - timedelta(days=7)
            interval = "day"
        elif period == "30d":
            start_time = now - timedelta(days=30)
            interval = "day"
        else:
            raise HTTPException(status_code=400, detail="Invalid period")
        
        # 기본 응답 (실제 데이터는 DB 연결 필요)
        return {
            "success": True,
            "site_id": site_id,
            "period": period,
            "interval": interval,
            "start_time": start_time.isoformat(),
            "end_time": now.isoformat(),
            "data": {
                "pageviews": {
                    "total": 0,
                    "trend": []
                },
                "visitors": {
                    "total": 0,
                    "unique": 0
                },
                "popular_pages": [],
                "referrers": [],
                "message": "데이터베이스 연결이 필요합니다. MySQL과 Redis를 시작해주세요."
            },
            "metadata": {
                "generated_at": now.isoformat(),
                "cache": False
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analytics query failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/")
async def analytics_info():
    """Analytics API 정보"""
    return {
        "service": "TrendStream Analytics API",
        "version": "1.0.0",
        "endpoints": {
            "site_analytics": "/api/analytics/{site_id}?period=1h",
            "supported_periods": ["1h", "24h", "7d", "30d"]
        },
        "status": "operational",
        "note": "데이터베이스가 연결되지 않아 실제 데이터를 제공할 수 없습니다."
    }

