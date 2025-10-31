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
    get_report_by_id
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
    신고 통계 데이터
    
    대시보드 카드에 표시할 요약 통계
    """
    try:
        reports = load_reports_db()
        
        # 상태별 통계
        pending_count = len([r for r in reports if r.get('status') == 'pending'])
        completed_count = len([r for r in reports if r.get('status') == 'completed'])
        rejected_count = len([r for r in reports if r.get('status') == 'rejected'])
        
        # 유형별 통계
        type_stats = {}
        for report in reports:
            report_type = report.get('reportType', '기타')
            type_stats[report_type] = type_stats.get(report_type, 0) + 1
        
        # AI 판단별 통계
        ai_result_stats = {}
        for report in reports:
            ai_result = report.get('aiAnalysis', {}).get('result', '부분일치')
            ai_result_stats[ai_result] = ai_result_stats.get(ai_result, 0) + 1
        
        return {
            'success': True,
            'data': {
                'status_stats': {
                    'pending': pending_count,
                    'completed': completed_count,
                    'rejected': rejected_count,
                    'total': len(reports)
                },
                'type_stats': type_stats,
                'ai_result_stats': ai_result_stats,
                'recent_reports': reports[-10:][::-1] if reports else []  # 최근 10개 (역순)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"통계 조회 중 오류: {str(e)}")

