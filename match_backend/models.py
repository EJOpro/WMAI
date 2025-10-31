"""
WMAA 데이터 모델 정의
"""

from pydantic import BaseModel
from typing import Optional


class ReportRequest(BaseModel):
    """신고 분석 요청"""
    post_content: str
    reason: str


class ReportResponse(BaseModel):
    """신고 분석 응답"""
    id: int
    post_content: str
    reason: str
    result_type: str
    score: int
    analysis: str
    css_class: str
    timestamp: str
    status: str
    post_action: Optional[str] = None


class ReportUpdateRequest(BaseModel):
    """신고 상태 업데이트 요청"""
    status: str
    processing_note: Optional[str] = None

