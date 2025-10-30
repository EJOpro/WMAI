"""트렌드 API 라우터"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from datetime import datetime
from typing import Optional
from backend.models.schemas import (
    Granularity, GroupBy, Metric,
    TimeseriesResponse, AnomaliesResponse, ForecastResponse,
    SearchKeywordRankingResponse,
    ErrorResponse
)
from backend.services.trends import trends_service
from backend.api.auth import verify_api_key
from loguru import logger
import uuid

router = APIRouter(prefix="/v1/trends", tags=["Trends"])


@router.get(
    "/timeseries",
    response_model=TimeseriesResponse,
    dependencies=[Depends(verify_api_key)],
    responses={
        200: {"model": TimeseriesResponse},
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse}
    }
)
async def get_timeseries(
    start: datetime = Query(..., description="시작 시각 (ISO8601 UTC)"),
    end: datetime = Query(..., description="종료 시각 (ISO8601 UTC)"),
    granularity: Granularity = Query(Granularity.ONE_HOUR, description="집계 단위"),
    metric: Metric = Query(Metric.PV, description="지표"),
    group_by: Optional[GroupBy] = Query(None, description="그룹화 차원"),
    top_k: int = Query(10, ge=1, le=100, description="상위 K개"),
    limit: int = Query(100, ge=1, le=1000, description="페이지 크기"),
    offset: int = Query(0, ge=0, description="오프셋")
):
    """
    시계열 트렌드 조회
    
    선택된 지표와 버킷 단위의 시계열을 차원별 시리즈로 반환합니다.
    기본적으로 상위 10개 항목만 제공됩니다.
    """
    request_id = str(uuid.uuid4())
    
    try:
        logger.info(f"[{request_id}] Timeseries query: {metric} {granularity} {start} to {end}")
        
        # 기간 검증
        if end <= start:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End time must be after start time"
            )
        
        # 시계열 조회
        series, total_count = trends_service.get_timeseries(
            start=start,
            end=end,
            granularity=granularity,
            metric=metric,
            group_by=group_by,
            top_k=top_k,
            limit=limit,
            offset=offset
        )
        
        return TimeseriesResponse(
            metric=metric,
            granularity=granularity,
            group_by=group_by,
            series=series,
            total_count=total_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] Timeseries query failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/anomalies",
    response_model=AnomaliesResponse,
    dependencies=[Depends(verify_api_key)],
    responses={
        200: {"model": AnomaliesResponse},
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse}
    }
)
async def get_anomalies(
    start: datetime = Query(..., description="시작 시각 (ISO8601 UTC)"),
    end: datetime = Query(..., description="종료 시각 (ISO8601 UTC)"),
    granularity: Granularity = Query(Granularity.ONE_HOUR, description="집계 단위"),
    metric: Metric = Query(Metric.PV, description="지표"),
    threshold: float = Query(2.5, ge=1.0, le=5.0, description="이상 탐지 임계값 (표준편차 배수)")
):
    """
    이상 탐지
    
    이동평균/계절성 보정 잔차 기반의 이상점 배열을 점수와 함께 반환합니다.
    """
    request_id = str(uuid.uuid4())
    
    try:
        logger.info(f"[{request_id}] Anomaly detection: {metric} {granularity} {start} to {end}")
        
        if end <= start:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End time must be after start time"
            )
        
        # 이상 탐지
        anomalies = trends_service.detect_anomalies(
            start=start,
            end=end,
            granularity=granularity,
            metric=metric,
            threshold=threshold
        )
        
        return AnomaliesResponse(
            metric=metric,
            granularity=granularity,
            anomalies=anomalies,
            total_count=len(anomalies)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] Anomaly detection failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/forecast",
    response_model=ForecastResponse,
    dependencies=[Depends(verify_api_key)],
    responses={
        200: {"model": ForecastResponse},
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse}
    }
)
async def get_forecast(
    start: datetime = Query(..., description="예측 시작 시각 (ISO8601 UTC)"),
    granularity: Granularity = Query(Granularity.ONE_HOUR, description="집계 단위"),
    metric: Metric = Query(Metric.PV, description="지표"),
    horizon_days: int = Query(7, ge=1, le=30, description="예측 수평선 (일)")
):
    """
    예측
    
    7일 또는 4주 수평선에 대한 예측값과 신뢰구간을 반환합니다.
    """
    request_id = str(uuid.uuid4())
    
    try:
        logger.info(f"[{request_id}] Forecast: {metric} {granularity} from {start} horizon={horizon_days}d")
        
        # 예측
        forecast_points = trends_service.forecast(
            start=start,
            granularity=granularity,
            metric=metric,
            horizon_days=horizon_days
        )
        
        return ForecastResponse(
            metric=metric,
            granularity=granularity,
            forecast_points=forecast_points,
            horizon_days=horizon_days
        )
        
    except Exception as e:
        logger.error(f"[{request_id}] Forecast failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/search-keywords",
    response_model=SearchKeywordRankingResponse,
    dependencies=[Depends(verify_api_key)],
    responses={
        200: {"model": SearchKeywordRankingResponse},
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse}
    }
)
async def get_search_keyword_ranking(
    start: datetime = Query(..., description="시작 시각 (ISO8601 UTC)"),
    end: datetime = Query(..., description="종료 시각 (ISO8601 UTC)"),
    top_k: int = Query(10, ge=1, le=100, description="상위 K개 검색어")
):
    """
    인기 검색어 랭킹 조회
    
    지정된 기간 동안 가장 많이 검색된 키워드를 순위별로 반환합니다.
    검색 이벤트는 event_type='search'이고 event_value에 검색어가 포함되어야 합니다.
    """
    request_id = str(uuid.uuid4())
    
    try:
        logger.info(f"[{request_id}] Search keyword ranking query: {start} to {end}, top {top_k}")
        
        # 기간 검증
        if end <= start:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End time must be after start time"
            )
        
        result = await trends_service.get_search_keyword_ranking(
            start=start,
            end=end,
            top_k=top_k
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] Search keyword ranking failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

