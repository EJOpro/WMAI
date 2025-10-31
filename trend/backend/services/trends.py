"""트렌드 조회 및 분석 서비스"""
from sqlalchemy import text
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import numpy as np
from backend.models.schemas import (
    Granularity, GroupBy, Metric, 
    TimeseriesSeries, TimeseriesPoint,
    AnomalyPoint, ForecastPoint,
    SearchKeywordRank, SearchKeywordRankingResponse
)
from backend.services.database import get_read_session
from backend.services.cache import cache_service


class TrendsService:
    """트렌드 조회 및 분석 서비스"""
    
    def _get_aggregation_table(self, granularity: Granularity) -> str:
        """집계 테이블 선택"""
        table_map = {
            Granularity.ONE_MINUTE: "agg_1m",
            Granularity.FIVE_MINUTES: "agg_5m",
            Granularity.ONE_HOUR: "agg_1h"
        }
        return table_map.get(granularity, "agg_1h")
    
    def _build_group_by_clause(self, group_by: Optional[GroupBy]) -> tuple[str, str]:
        """GROUP BY 절 및 차원 컬럼 생성"""
        if not group_by:
            return "", "overall"
        
        dimension_map = {
            GroupBy.PAGE: ("page_id", "dim_page.page_path"),
            GroupBy.UTM: ("utm_id", "CONCAT_WS('/', dim_utm.utm_source, dim_utm.utm_medium, dim_utm.utm_campaign)"),
            GroupBy.DEVICE: ("device_id", "dim_device.device_name"),
            GroupBy.COUNTRY: ("country_id", "dim_country.country_iso2")
        }
        
        id_col, value_col = dimension_map[group_by]
        return id_col, value_col
    
    def _build_join_clauses(self, group_by: Optional[GroupBy]) -> str:
        """JOIN 절 생성"""
        if not group_by:
            return ""
        
        join_map = {
            GroupBy.PAGE: "LEFT JOIN dim_page ON agg.page_id = dim_page.page_id",
            GroupBy.UTM: "LEFT JOIN dim_utm ON agg.utm_id = dim_utm.utm_id",
            GroupBy.DEVICE: "LEFT JOIN dim_device ON agg.device_id = dim_device.device_id",
            GroupBy.COUNTRY: "LEFT JOIN dim_country ON agg.country_id = dim_country.country_id"
        }
        
        return join_map.get(group_by, "")
    
    def get_timeseries(
        self,
        start: datetime,
        end: datetime,
        granularity: Granularity,
        metric: Metric,
        group_by: Optional[GroupBy] = None,
        top_k: int = 10,
        limit: int = 100,
        offset: int = 0
    ) -> tuple[List[TimeseriesSeries], int]:
        """
        시계열 데이터 조회
        
        Returns:
            (시리즈 목록, 전체 개수)
        """
        # 캐시 확인
        cache_key = cache_service._generate_key(
            "timeseries",
            start=start.isoformat(),
            end=end.isoformat(),
            granularity=granularity.value,
            metric=metric.value,
            group_by=group_by.value if group_by else None,
            top_k=top_k,
            limit=limit,
            offset=offset
        )
        
        cached = cache_service.get(cache_key)
        if cached:
            return cached["series"], cached["total_count"]
        
        table = self._get_aggregation_table(granularity)
        group_col, value_col = self._build_group_by_clause(group_by)
        join_clause = self._build_join_clauses(group_by)
        
        # 메트릭 컬럼 선택
        metric_col_map = {
            Metric.PV: "SUM(pv)",
            Metric.UV: "SUM(pv)",  # HLL 카디널리티는 추후 구현
            Metric.SESSIONS: "SUM(sessions)",
            Metric.CONVERSION_RATE: "SUM(conv) / NULLIF(SUM(sessions), 0) * 100"
        }
        metric_col = metric_col_map[metric]
        
        with get_read_session() as session:
            if group_by:
                # 차원별 그룹화
                query = text(f"""
                    SELECT 
                        bucket_ts,
                        {value_col} as dimension_value,
                        {metric_col} as value
                    FROM {table} agg
                    {join_clause}
                    WHERE bucket_ts >= :start AND bucket_ts < :end
                        AND {group_col} IS NOT NULL
                    GROUP BY bucket_ts, {group_col}
                    ORDER BY bucket_ts, value DESC
                    LIMIT :limit OFFSET :offset
                """)
                
                result = session.execute(
                    query,
                    {"start": start, "end": end, "limit": limit, "offset": offset}
                ).fetchall()
                
                # 시리즈별로 데이터 구성
                series_dict: Dict[str, List[TimeseriesPoint]] = {}
                for row in result:
                    dim_value = row.dimension_value or "unknown"
                    if dim_value not in series_dict:
                        series_dict[dim_value] = []
                    series_dict[dim_value].append(
                        TimeseriesPoint(ts=row.bucket_ts, value=float(row.value or 0))
                    )
                
                # 상위 K개 선택
                if top_k > 0:
                    # 총합 기준으로 정렬
                    sorted_dims = sorted(
                        series_dict.items(),
                        key=lambda x: sum(p.value for p in x[1]),
                        reverse=True
                    )[:top_k]
                    series_dict = dict(sorted_dims)
                
                series = [
                    TimeseriesSeries(
                        dimension_key=group_by.value,
                        dimension_value=dim_value,
                        points=points
                    )
                    for dim_value, points in series_dict.items()
                ]
                
            else:
                # 전체 집계
                query = text(f"""
                    SELECT 
                        bucket_ts,
                        {metric_col} as value
                    FROM {table} agg
                    WHERE bucket_ts >= :start AND bucket_ts < :end
                    GROUP BY bucket_ts
                    ORDER BY bucket_ts
                """)
                
                result = session.execute(query, {"start": start, "end": end}).fetchall()
                
                points = [
                    TimeseriesPoint(ts=row.bucket_ts, value=float(row.value or 0))
                    for row in result
                ]
                
                series = [
                    TimeseriesSeries(
                        dimension_key="overall",
                        dimension_value="all",
                        points=points
                    )
                ]
            
            total_count = len(series)
        
        # 캐시 저장
        cache_service.set(cache_key, {"series": [s.dict() for s in series], "total_count": total_count})
        
        return series, total_count
    
    def detect_anomalies(
        self,
        start: datetime,
        end: datetime,
        granularity: Granularity,
        metric: Metric,
        threshold: float = 2.5
    ) -> List[AnomalyPoint]:
        """
        이상 탐지 (이동평균 기반)
        
        Args:
            threshold: 표준편차 기준 임계값
        """
        # 시계열 데이터 조회
        series, _ = self.get_timeseries(
            start=start - timedelta(days=7),  # 이전 데이터 포함
            end=end,
            granularity=granularity,
            metric=metric,
            group_by=None
        )
        
        if not series or not series[0].points:
            return []
        
        points = series[0].points
        values = np.array([p.value for p in points])
        timestamps = [p.ts for p in points]
        
        # 이동평균 및 표준편차
        window = min(12, len(values) // 4)  # 최소 12개 윈도우
        if window < 3:
            return []
        
        moving_avg = np.convolve(values, np.ones(window) / window, mode='valid')
        moving_std = np.array([
            np.std(values[max(0, i-window):i+1])
            for i in range(len(values))
        ])
        
        # 이상점 탐지
        anomalies = []
        for i in range(window - 1, len(values)):
            expected = moving_avg[i - window + 1]
            actual = values[i]
            std = moving_std[i]
            
            if std > 0:
                z_score = abs(actual - expected) / std
                if z_score > threshold:
                    anomaly_score = min(z_score / 10, 1.0)  # 0~1 정규화
                    anomalies.append(
                        AnomalyPoint(
                            ts=timestamps[i],
                            expected=float(expected),
                            actual=float(actual),
                            anomaly_score=float(anomaly_score)
                        )
                    )
        
        # 지정된 기간 내 이상점만 반환
        anomalies = [a for a in anomalies if start <= a.ts < end]
        
        return anomalies
    
    def forecast(
        self,
        start: datetime,
        granularity: Granularity,
        metric: Metric,
        horizon_days: int = 7
    ) -> List[ForecastPoint]:
        """
        간단한 예측 (이동평균 기반)
        
        실제 운영 환경에서는 Prophet, ARIMA 등 사용 권장
        """
        # 과거 데이터 조회 (horizon의 4배)
        lookback_days = horizon_days * 4
        historical_start = start - timedelta(days=lookback_days)
        
        series, _ = self.get_timeseries(
            start=historical_start,
            end=start,
            granularity=granularity,
            metric=metric,
            group_by=None
        )
        
        if not series or not series[0].points:
            return []
        
        points = series[0].points
        values = np.array([p.value for p in points])
        
        # 간단한 예측: 최근 평균과 트렌드
        recent_mean = np.mean(values[-min(len(values), 20):])
        recent_std = np.std(values[-min(len(values), 20):])
        
        # 시간 단위에 따른 예측 간격
        if granularity == Granularity.ONE_HOUR:
            intervals = horizon_days * 24
            delta = timedelta(hours=1)
        elif granularity == Granularity.FIVE_MINUTES:
            intervals = horizon_days * 24 * 12
            delta = timedelta(minutes=5)
        else:
            intervals = horizon_days * 24 * 60
            delta = timedelta(minutes=1)
        
        forecast_points = []
        current_ts = start
        
        for _ in range(min(intervals, 168)):  # 최대 7일 (시간 단위)
            forecast_value = recent_mean
            lower = max(0, forecast_value - 1.96 * recent_std)
            upper = forecast_value + 1.96 * recent_std
            
            forecast_points.append(
                ForecastPoint(
                    ts=current_ts,
                    forecast=float(forecast_value),
                    lower_bound=float(lower),
                    upper_bound=float(upper)
                )
            )
            
            current_ts += delta
        
        return forecast_points
    
    async def get_search_keyword_ranking(
        self,
        start: datetime,
        end: datetime,
        top_k: int = 10
    ) -> SearchKeywordRankingResponse:
        """
        인기 검색어 랭킹 조회
        
        Args:
            start: 시작 시각
            end: 종료 시각
            top_k: 상위 K개 검색어
            
        Returns:
            SearchKeywordRankingResponse: 검색어 랭킹 응답
        """
        # 캐시 키 생성
        cache_key = f"search_keywords:{start.isoformat()}:{end.isoformat()}:{top_k}"
        
        # 캐시 확인
        cached = cache_service.get(cache_key)
        if cached:
            return SearchKeywordRankingResponse(**cached)
        
        # 검색 이벤트에서 검색어 추출 및 집계
        query = text("""
            SELECT 
                JSON_UNQUOTE(JSON_EXTRACT(event_value, '$.keyword')) AS keyword,
                COUNT(*) AS search_count
            FROM fact_events
            WHERE event_type = 'search'
              AND event_time >= :start
              AND event_time < :end
              AND event_value IS NOT NULL
              AND JSON_EXTRACT(event_value, '$.keyword') IS NOT NULL
            GROUP BY keyword
            ORDER BY search_count DESC
            LIMIT :top_k
        """)
        
        with get_read_session() as session:
            result = session.execute(
                query,
                {
                    "start": start,
                    "end": end,
                    "top_k": top_k
                }
            )
            rows = result.fetchall()
        
        # 전체 검색 횟수 계산
        total_searches = sum(row[1] for row in rows)
        
        # 순위 생성
        rankings = [
            SearchKeywordRank(
                rank=idx + 1,
                keyword=row[0],
                count=row[1],
                change=None  # 순위 변동은 이전 기간 데이터와 비교 필요
            )
            for idx, row in enumerate(rows)
        ]
        
        response = SearchKeywordRankingResponse(
            start=start,
            end=end,
            rankings=rankings,
            total_searches=total_searches
        )
        
        # 캐시 저장
        cache_service.set(cache_key, response.model_dump())
        
        return response


# 싱글톤 인스턴스
trends_service = TrendsService()

