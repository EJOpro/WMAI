"""
🔍 WMAA (신고 검증) API 라우터
match_backend 모듈을 사용하여 신고 검증 기능 제공
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import os
from dotenv import load_dotenv

# 환경 변수 로드 (프로젝트 루트의 match_config.env 파일)
env_path = os.path.join(os.path.dirname(__file__), '../../match_config.env')
load_dotenv(env_path)

# WMAA 백엔드 모듈 import
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from match_backend.core import (
    analyze_with_ai,
    save_report_to_db,
    load_reports_db,
    save_reports_db,
    update_report_status,
    get_report_by_id,
    get_reports_with_filters,
    get_dashboard_stats
)
from match_backend.models import ReportRequest, ReportResponse

router = APIRouter(tags=["wmaa"])

# ============================================
# 🔍 신고 분석 API
# ============================================

@router.post("/analyze", response_model=ReportResponse)
async def analyze_report(report: ReportRequest):
    """
    신고 내용 AI 분석
    
    - OpenAI GPT-4o-mini를 사용하여 게시글과 신고 내용의 일치 여부 분석
    - 일치/불일치/부분일치로 판단
    - 결과를 DB에 자동 저장
    """
    try:
        # API 키 확인
        api_key = os.getenv('OPENAI_API_KEY', '')
        if not api_key or api_key == 'your-api-key-here':
            raise HTTPException(
                status_code=500, 
                detail="OpenAI API 키가 설정되지 않았습니다. match_config.env 파일에 실제 API 키를 입력하세요."
            )
        
        # AI 분석 수행
        result = analyze_with_ai(report.post_content, report.reason)
        
        # 데이터베이스에 저장
        saved_report = save_report_to_db(report.post_content, report.reason, result)
        
        return ReportResponse(
            id=saved_report['id'],
            post_content=report.post_content,
            reason=report.reason,
            result_type=result['type'],
            score=result['score'],
            analysis=result['analysis'],
            css_class=result['css_class'],
            timestamp=saved_report['reportDate'],
            status=saved_report['status'],
            post_action=saved_report.get('postAction')
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# 📋 예시 데이터 API
# ============================================

@router.get("/examples")
async def get_examples():
    """
    신고 예시 데이터 반환
    
    프론트엔드에서 빠른 테스트를 위한 예시 데이터 제공
    """
    examples = {
        "1": {
            "post": "이 제품은 정말 최고입니다! 100% 천연 성분으로만 만들어졌고, 부작용이 전혀 없어요. 의사들도 추천하는 제품이라고 하네요. 지금 주문하면 50% 할인해드려요!",
            "reason": "도배 및 광고",
            "button_text": "📢 도배 및 광고"
        },
        "2": {
            "post": "오늘 날씨가 정말 좋네요. 공원에서 산책하면서 좋은 시간을 보냈습니다. 가족들과 함께 피크닉도 했어요.",
            "reason": "욕설 및 비방",
            "button_text": "💬 욕설 및 비방"
        },
        "3": {
            "post": "김철수씨는 서울시 강남구 테헤란로 123번지에 살고 있으며, 전화번호는 010-1234-5678입니다. 최근 이혼 소송 중이라고 하네요.",
            "reason": "사생활 침해",
            "button_text": "🔒 사생활 침해"
        },
        "4": {
            "post": "유명 작가의 최신 소설 전문을 공유합니다. [소설 전체 내용 무단 게재]",
            "reason": "저작권 침해",
            "button_text": "©️ 저작권 침해"
        }
    }
    return examples


# ============================================
# 📊 관리자 API - 신고 목록
# ============================================

@router.get("/reports/list")
async def get_reports_list():
    """
    전체 신고 목록 조회
    
    관리자 대시보드에서 사용
    """
    try:
        reports = load_reports_db()
        return {
            'success': True,
            'data': reports,
            'total': len(reports)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"데이터 로드 중 오류: {str(e)}")


@router.get("/reports/detail/{report_id}")
async def get_report_detail(report_id: int):
    """
    특정 신고 상세 조회
    
    - report_id: 신고 ID
    """
    try:
        report = get_report_by_id(report_id)
        
        if report:
            return {
                'success': True,
                'data': report
            }
        else:
            raise HTTPException(status_code=404, detail="신고를 찾을 수 없습니다.")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"조회 중 오류: {str(e)}")


# ============================================
# ✏️ 관리자 API - 신고 상태 업데이트
# ============================================

@router.put("/reports/update/{report_id}")
async def update_report(
    report_id: int, 
    status: str = Query(..., description="신고 상태 (completed, rejected, pending)"),
    processing_note: Optional[str] = Query(None, description="처리 메모")
):
    """
    신고 상태 업데이트
    
    - report_id: 신고 ID
    - status: 새로운 상태 (completed=승인, rejected=반려, pending=대기)
    - processing_note: 처리 메모 (선택사항)
    
    부분일치로 판단된 신고를 관리자가 수동으로 승인/반려 처리할 때 사용
    """
    try:
        # 상태 유효성 검증
        valid_statuses = ['completed', 'rejected', 'pending']
        if status not in valid_statuses:
            raise HTTPException(
                status_code=400, 
                detail=f"유효하지 않은 상태입니다. {valid_statuses} 중 하나를 선택하세요."
            )
        
        # 신고 상태 업데이트
        updated_report = update_report_status(report_id, status, processing_note)
        
        return {
            'success': True,
            'data': updated_report,
            'message': '신고가 성공적으로 업데이트되었습니다.'
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"업데이트 중 오류: {str(e)}")


# ============================================
# 📈 통계 API
# ============================================

@router.get("/reports/stats")
async def get_reports_stats():
    """
    신고 통계 데이터 (MySQL 기반)
    
    대시보드 카드에 표시할 요약 통계
    """
    try:
        stats = get_dashboard_stats()
        
        return {
            'success': True,
            'data': {
                'status_stats': {
                    'pending': stats['basic_stats'].get('pending_reports', 0),
                    'completed': stats['basic_stats'].get('completed_reports', 0),
                    'rejected': stats['basic_stats'].get('rejected_reports', 0),
                    'total': stats['basic_stats'].get('total_reports', 0)
                },
                'type_stats': stats['type_stats'],
                'ai_result_stats': stats['ai_stats'],
                'daily_trends': stats['daily_trends'],
                'avg_processing_hours': stats['avg_processing_hours']
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"통계 조회 중 오류: {str(e)}")


# ============================================
# 📋 관리자 API - 필터링된 신고 목록
# ============================================

@router.get("/reports/filtered")
async def get_filtered_reports(
    status: Optional[str] = Query(None, description="상태 필터 (pending, completed, rejected)"),
    report_type: Optional[str] = Query(None, description="신고 유형 필터"),
    ai_result: Optional[str] = Query(None, description="AI 결과 필터 (match, partial_match, mismatch)"),
    start_date: Optional[str] = Query(None, description="시작 날짜 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="종료 날짜 (YYYY-MM-DD)"),
    limit: int = Query(25, description="페이지 크기", ge=1, le=100),
    offset: int = Query(0, description="오프셋", ge=0)
):
    """
    필터링된 신고 목록 조회
    
    관리자 페이지에서 다양한 조건으로 신고를 필터링하여 조회
    """
    try:
        # AI 결과 필터를 MySQL enum 형식으로 변환
        mysql_ai_result = None
        if ai_result:
            ai_result_mapping = {
                '일치': 'match',
                '부분일치': 'partial_match',
                '불일치': 'mismatch'
            }
            mysql_ai_result = ai_result_mapping.get(ai_result, ai_result)
        
        result = get_reports_with_filters(
            status_filter=status,
            type_filter=report_type,
            ai_result_filter=mysql_ai_result,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )
        
        return {
            'success': True,
            'data': result['reports'],
            'pagination': {
                'total': result['total'],
                'limit': result['limit'],
                'offset': result['offset'],
                'has_more': result['offset'] + result['limit'] < result['total']
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"필터링된 신고 조회 중 오류: {str(e)}")


# ============================================
# 📊 관리자 API - 대시보드 통계
# ============================================

@router.get("/dashboard/stats")
async def get_dashboard_statistics():
    """
    관리자 대시보드용 상세 통계
    
    차트와 지표에 사용할 상세한 통계 데이터
    """
    try:
        stats = get_dashboard_stats()
        
        return {
            'success': True,
            'data': stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"대시보드 통계 조회 중 오류: {str(e)}")

