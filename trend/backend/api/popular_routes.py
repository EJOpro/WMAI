from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
import httpx
import asyncio
from datetime import datetime, timedelta
import json

router = APIRouter(prefix="/popular", tags=["popular"])

# dad.dothome.co.kr 인기검색어 API URL
POPULAR_API_URL = "https://dad.dothome.co.kr/adm/popular_api.php"

@router.get("/test")
async def test_popular_api():
    """인기검색어 API 테스트"""
    return {"message": "Popular API is working!", "timestamp": datetime.now().isoformat()}

@router.get("/keywords")
async def get_popular_keywords(
    page: int = Query(1, ge=1, description="페이지 번호"),
    limit: int = Query(20, ge=1, le=100, description="페이지당 항목 수"),
    search: Optional[str] = Query(None, description="검색어"),
    search_field: str = Query("pp_word", description="검색 필드 (pp_word, pp_date)"),
    sort: str = Query("pp_id", description="정렬 필드"),
    order: str = Query("desc", description="정렬 순서 (asc, desc)"),
    days: int = Query(7, ge=1, le=365, description="조회할 일수")
):
    """인기검색어 조회"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            params = {
                "page": page,
                "limit": limit,
                "sort": sort,
                "order": order
            }
            
            if search:
                params["search"] = search
                params["search_field"] = search_field
            
            response = await client.get(POPULAR_API_URL, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get("success", False):
                raise HTTPException(status_code=400, detail=data.get("error", "API 오류"))
            
            # 최근 N일 데이터 필터링
            if days < 365:
                cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
                filtered_data = [
                    item for item in data.get("data", [])
                    if item.get("date", "") >= cutoff_date
                ]
                data["data"] = filtered_data
                data["pagination"]["total_count"] = len(filtered_data)
            
            return {
                "success": True,
                "data": data.get("data", []),
                "pagination": data.get("pagination", {}),
                "filters": data.get("filters", {}),
                "source": "dad.dothome.co.kr"
            }
            
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="외부 API 응답 시간 초과")
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"외부 API 연결 실패: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")

@router.get("/keywords/trending")
async def get_trending_keywords(
    limit: int = Query(10, ge=1, le=50, description="조회할 항목 수"),
    hours: int = Query(24, ge=1, le=168, description="조회할 시간 (시간)")
):
    """트렌딩 검색어 조회"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            params = {
                "limit": limit,
                "sort": "pp_date",
                "order": "desc"
            }
            
            response = await client.get(POPULAR_API_URL, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get("success", False):
                raise HTTPException(status_code=400, detail=data.get("error", "API 오류"))
            
            # 최근 N시간 데이터 필터링
            cutoff_time = datetime.now() - timedelta(hours=hours)
            trending_keywords = []
            
            for item in data.get("data", []):
                try:
                    item_date = datetime.strptime(item.get("date", ""), "%Y-%m-%d")
                    if item_date >= cutoff_time:
                        trending_keywords.append(item)
                except ValueError:
                    continue
            
            return {
                "success": True,
                "data": trending_keywords[:limit],
                "period_hours": hours,
                "source": "dad.dothome.co.kr"
            }
            
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="외부 API 응답 시간 초과")
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"외부 API 연결 실패: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")

@router.get("/keywords/stats")
async def get_keywords_stats():
    """인기검색어 통계"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 전체 데이터 조회
            response = await client.get(POPULAR_API_URL, params={"limit": 1000})
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get("success", False):
                raise HTTPException(status_code=400, detail=data.get("error", "API 오류"))
            
            keywords_data = data.get("data", [])
            
            # 통계 계산
            total_keywords = len(keywords_data)
            today = datetime.now().strftime("%Y-%m-%d")
            today_keywords = len([k for k in keywords_data if k.get("date") == today])
            
            # 최근 7일 데이터
            week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            week_keywords = len([k for k in keywords_data if k.get("date", "") >= week_ago])
            
            # 최근 30일 데이터
            month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            month_keywords = len([k for k in keywords_data if k.get("date", "") >= month_ago])
            
            return {
                "success": True,
                "stats": {
                    "total_keywords": total_keywords,
                    "today_keywords": today_keywords,
                    "week_keywords": week_keywords,
                    "month_keywords": month_keywords,
                    "last_updated": datetime.now().isoformat()
                },
                "source": "dad.dothome.co.kr"
            }
            
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="외부 API 응답 시간 초과")
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"외부 API 연결 실패: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")

@router.post("/keywords/sync")
async def sync_keywords():
    """인기검색어 데이터 동기화 (향후 자동화용)"""
    try:
        # 현재는 단순히 API 호출로 동기화 상태 확인
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(POPULAR_API_URL, params={"limit": 1})
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get("success", False):
                raise HTTPException(status_code=400, detail="외부 API 오류")
            
            return {
                "success": True,
                "message": "인기검색어 API 연결 확인 완료",
                "last_sync": datetime.now().isoformat(),
                "source": "dad.dothome.co.kr"
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"동기화 실패: {str(e)}")
