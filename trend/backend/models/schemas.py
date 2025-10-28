"""데이터 스키마 및 Pydantic 모델"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class DeviceType(str, Enum):
    """디바이스 타입"""
    DESKTOP = "desktop"
    MOBILE = "mobile"
    TABLET = "tablet"


class EventType(str, Enum):
    """이벤트 타입"""
    PAGEVIEW = "pageview"
    CLICK = "click"
    CONVERSION = "conversion"
    CUSTOM = "custom"


class EventSchema(BaseModel):
    """수집 이벤트 스키마"""
    event_time: datetime = Field(..., description="이벤트 발생 시각 (ISO8601 UTC)")
    session_id: str = Field(..., min_length=36, max_length=36, description="세션 UUID")
    user_hash: str = Field(..., min_length=64, max_length=64, description="익명화된 사용자 해시")
    page_path: str = Field(..., max_length=2048, description="페이지 경로")
    referrer: Optional[str] = Field(None, max_length=2048, description="리퍼러")
    utm_source: Optional[str] = Field(None, max_length=255, description="UTM 소스")
    utm_medium: Optional[str] = Field(None, max_length=255, description="UTM 미디엄")
    utm_campaign: Optional[str] = Field(None, max_length=255, description="UTM 캠페인")
    device: DeviceType = Field(..., description="디바이스 타입")
    country_iso2: str = Field(..., min_length=2, max_length=2, description="국가 ISO2 코드")
    event_type: str = Field(..., max_length=50, description="이벤트 타입")
    event_value: Optional[Dict[str, Any]] = Field(None, description="이벤트 값 (JSON)")
    schema_version: str = Field(default="1.0", description="스키마 버전")
    
    @validator('country_iso2')
    def country_iso2_uppercase(cls, v):
        """ISO2 코드를 대문자로 변환"""
        return v.upper()


class BatchEventsRequest(BaseModel):
    """배치 이벤트 수집 요청"""
    events: List[EventSchema] = Field(..., min_items=1, max_items=1000, description="이벤트 배열")


class Granularity(str, Enum):
    """집계 단위"""
    ONE_MINUTE = "1m"
    FIVE_MINUTES = "5m"
    ONE_HOUR = "1h"
    ONE_DAY = "1d"


class GroupBy(str, Enum):
    """그룹화 차원"""
    PAGE = "page"
    UTM = "utm"
    DEVICE = "device"
    COUNTRY = "country"


class Metric(str, Enum):
    """지표 타입"""
    PV = "pv"
    UV = "uv"
    SESSIONS = "sessions"
    CONVERSION_RATE = "conversion_rate"


class TimeseriesPoint(BaseModel):
    """시계열 데이터 포인트"""
    ts: datetime = Field(..., description="타임스탬프")
    value: float = Field(..., description="지표 값")


class TimeseriesSeries(BaseModel):
    """시계열 시리즈"""
    dimension_key: str = Field(..., description="차원 키 (예: page_path, utm_source)")
    dimension_value: str = Field(..., description="차원 값")
    points: List[TimeseriesPoint] = Field(..., description="데이터 포인트 배열")


class TimeseriesResponse(BaseModel):
    """시계열 API 응답"""
    metric: Metric = Field(..., description="지표")
    granularity: Granularity = Field(..., description="집계 단위")
    group_by: Optional[GroupBy] = Field(None, description="그룹화 차원")
    series: List[TimeseriesSeries] = Field(..., description="시계열 시리즈 배열")
    total_count: int = Field(..., description="전체 시리즈 수")


class AnomalyPoint(BaseModel):
    """이상점 데이터"""
    ts: datetime = Field(..., description="타임스탬프")
    expected: float = Field(..., description="예상 값")
    actual: float = Field(..., description="실제 값")
    anomaly_score: float = Field(..., description="이상 점수 (0~1)")
    dimension_key: Optional[str] = Field(None, description="차원 키")
    dimension_value: Optional[str] = Field(None, description="차원 값")


class AnomaliesResponse(BaseModel):
    """이상 탐지 API 응답"""
    metric: Metric = Field(..., description="지표")
    granularity: Granularity = Field(..., description="집계 단위")
    anomalies: List[AnomalyPoint] = Field(..., description="이상점 배열")
    total_count: int = Field(..., description="이상점 총 개수")


class ForecastPoint(BaseModel):
    """예측 데이터 포인트"""
    ts: datetime = Field(..., description="예측 타임스탬프")
    forecast: float = Field(..., description="예측 값")
    lower_bound: float = Field(..., description="신뢰 구간 하한")
    upper_bound: float = Field(..., description="신뢰 구간 상한")


class ForecastResponse(BaseModel):
    """예측 API 응답"""
    metric: Metric = Field(..., description="지표")
    granularity: Granularity = Field(..., description="집계 단위")
    forecast_points: List[ForecastPoint] = Field(..., description="예측 포인트 배열")
    horizon_days: int = Field(..., description="예측 수평선 (일)")


class ErrorResponse(BaseModel):
    """에러 응답"""
    error: str = Field(..., description="에러 메시지")
    detail: Optional[str] = Field(None, description="상세 정보")
    request_id: Optional[str] = Field(None, description="요청 ID")


class SearchKeywordRank(BaseModel):
    """검색어 순위 항목"""
    rank: int = Field(..., description="순위")
    keyword: str = Field(..., description="검색어")
    count: int = Field(..., description="검색 횟수")
    change: Optional[int] = Field(None, description="순위 변동 (양수: 상승, 음수: 하락)")


class SearchKeywordRankingResponse(BaseModel):
    """검색어 랭킹 API 응답"""
    start: datetime = Field(..., description="시작 시각")
    end: datetime = Field(..., description="종료 시각")
    rankings: List[SearchKeywordRank] = Field(..., description="검색어 순위 목록")
    total_searches: int = Field(..., description="전체 검색 횟수")


# ============================================
# 커뮤니티 트렌드 분석 스키마
# ============================================

class CommunityPostSchema(BaseModel):
    """커뮤니티 게시글 스키마"""
    community_name: str = Field(..., max_length=100, description="커뮤니티명 (예: 루리웹)")
    board_name: Optional[str] = Field(None, max_length=100, description="게시판명")
    title: str = Field(..., max_length=500, description="게시글 제목")
    content: str = Field(..., description="게시글 본문")
    author: Optional[str] = Field(None, max_length=100, description="작성자")
    post_url: Optional[str] = Field(None, max_length=500, description="게시글 URL")
    view_count: int = Field(default=0, ge=0, description="조회수")
    like_count: int = Field(default=0, ge=0, description="좋아요 수")
    posted_at: datetime = Field(..., description="게시 시각 (ISO8601 UTC)")


class BatchPostsRequest(BaseModel):
    """배치 게시글 수집 요청"""
    posts: List[CommunityPostSchema] = Field(..., min_items=1, max_items=100, description="게시글 배열")


class CommentSchema(BaseModel):
    """댓글 스키마"""
    post_id: int = Field(..., description="게시글 ID")
    content: str = Field(..., description="댓글 내용")
    author: Optional[str] = Field(None, max_length=100, description="작성자")
    like_count: int = Field(default=0, ge=0, description="좋아요 수")
    commented_at: datetime = Field(..., description="댓글 작성 시각 (ISO8601 UTC)")


class BatchCommentsRequest(BaseModel):
    """배치 댓글 수집 요청"""
    comments: List[CommentSchema] = Field(..., min_items=1, max_items=500, description="댓글 배열")


class WordCloudItem(BaseModel):
    """워드클라우드 단어 항목"""
    word: str = Field(..., description="단어")
    frequency: int = Field(..., description="빈도수")
    weight: float = Field(..., description="가중치 (0~1)")


class WordCloudResponse(BaseModel):
    """워드클라우드 API 응답"""
    start: datetime = Field(..., description="분석 시작 시각")
    end: datetime = Field(..., description="분석 종료 시각")
    community: Optional[str] = Field(None, description="커뮤니티명 (필터)")
    board: Optional[str] = Field(None, description="게시판명 (필터)")
    words: List[WordCloudItem] = Field(..., description="워드클라우드 단어 배열")
    total_posts: int = Field(..., description="분석된 게시글 수")
    total_comments: int = Field(..., description="분석된 댓글 수")


class KeywordTimelinePoint(BaseModel):
    """키워드 타임라인 데이터 포인트"""
    ts: datetime = Field(..., description="타임스탬프")
    count: int = Field(..., description="언급 횟수")
    trend: Optional[float] = Field(None, description="트렌드 지표 (전일 대비 %, 선택)")


class KeywordTimelineSeries(BaseModel):
    """키워드 타임라인 시리즈"""
    keyword: str = Field(..., description="키워드")
    points: List[KeywordTimelinePoint] = Field(..., description="타임라인 데이터 포인트")
    total_count: int = Field(..., description="전체 언급 횟수")
    peak_count: int = Field(..., description="최대 언급 횟수")
    peak_ts: Optional[datetime] = Field(None, description="최대 언급 시각")


class TimelineResponse(BaseModel):
    """타임라인 API 응답"""
    start: datetime = Field(..., description="시작 시각")
    end: datetime = Field(..., description="종료 시각")
    granularity: str = Field(..., description="집계 단위 (1h, 1d, 1w)")
    community: Optional[str] = Field(None, description="커뮤니티명 (필터)")
    board: Optional[str] = Field(None, description="게시판명 (필터)")
    series: List[KeywordTimelineSeries] = Field(..., description="키워드별 타임라인")


class CommunityStatsResponse(BaseModel):
    """커뮤니티 통계 API 응답"""
    community_name: str = Field(..., description="커뮤니티명")
    total_posts: int = Field(..., description="전체 게시글 수")
    total_comments: int = Field(..., description="전체 댓글 수")
    date_range_start: Optional[datetime] = Field(None, description="데이터 시작일")
    date_range_end: Optional[datetime] = Field(None, description="데이터 종료일")
    boards: List[Dict[str, Any]] = Field(default_factory=list, description="게시판별 통계")
