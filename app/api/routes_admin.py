"""
관리자 API 라우터
신고 관리 및 처리
"""
from fastapi import APIRouter, Request, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.auth import require_admin, get_current_user
from app.database import execute_query

router = APIRouter(tags=["admin"])


class ReportProcessRequest(BaseModel):
    """신고 처리 요청"""
    action: str  # 'approve', 'reject'
    note: Optional[str] = None


@router.get("/admin/me")
async def check_admin(request: Request):
    """현재 사용자의 관리자 여부 확인"""
    user = get_current_user(request)
    if not user:
        return {'is_admin': False}
    
    # DB에서 role 확인
    user_data = execute_query(
        "SELECT role FROM users WHERE id = %s",
        (user['user_id'],),
        fetch_one=True
    )
    
    return {
        'is_admin': user_data['role'] == 'admin' if user_data else False,
        'user': user
    }


@router.get("/admin/reports")
async def get_reports(
    request: Request,
    status_filter: Optional[str] = None,
    type_filter: Optional[str] = None,
    page: int = 1,
    limit: int = 20
):
    """신고 목록 조회 (관리자 전용)"""
    require_admin(request)
    
    # 쿼리 작성
    conditions = []
    params = []
    
    if status_filter and status_filter in ['pending', 'reviewing', 'completed', 'rejected']:
        conditions.append("r.status = %s")
        params.append(status_filter)
    
    if type_filter and type_filter in ['board', 'comment']:
        conditions.append("r.report_type = %s")
        params.append(type_filter)
    
    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    # 총 개수
    count_query = f"SELECT COUNT(*) as total FROM report r {where_clause}"
    total_result = execute_query(count_query, tuple(params), fetch_one=True)
    total = total_result['total']
    
    # 목록 조회
    offset = (page - 1) * limit
    params.extend([limit, offset])
    
    query = f"""
        SELECT 
            r.id,
            r.report_type,
            r.board_id,
            r.comment_id,
            r.report_reason,
            r.report_detail,
            r.reported_content,
            r.status,
            r.priority,
            r.created_at,
            r.processed_date,
            r.processing_note,
            r.post_action,
            reporter.username as reporter_name,
            b.title as board_title,
            b.status as board_status,
            c.content as comment_content,
            c.status as comment_status
        FROM report r
        LEFT JOIN users reporter ON r.reporter_id = reporter.id
        LEFT JOIN board b ON r.board_id = b.id
        LEFT JOIN comment c ON r.comment_id = c.id
        {where_clause}
        ORDER BY r.created_at DESC
        LIMIT %s OFFSET %s
    """
    
    reports = execute_query(query, tuple(params), fetch_all=True)
    
    return {
        'success': True,
        'reports': reports,
        'pagination': {
            'total': total,
            'page': page,
            'limit': limit,
            'total_pages': (total + limit - 1) // limit
        }
    }


@router.post("/admin/reports/{report_id}/process")
async def process_report(request: Request, report_id: int, data: ReportProcessRequest):
    """신고 처리 (관리자 전용)"""
    admin_user = require_admin(request)
    
    # 신고 조회
    report = execute_query("""
        SELECT id, report_type, board_id, comment_id, status
        FROM report
        WHERE id = %s
    """, (report_id,), fetch_one=True)
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="신고를 찾을 수 없습니다"
        )
    
    if report['status'] in ['completed', 'rejected']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 처리된 신고입니다"
        )
    
    # 처리 액션
    if data.action == 'approve':
        # 승인: 게시물/댓글 차단
        new_status = 'completed'
        post_action = 'block'
        
        if report['report_type'] == 'board' and report['board_id']:
            execute_query(
                "UPDATE board SET status = 'blocked' WHERE id = %s",
                (report['board_id'],)
            )
        elif report['report_type'] == 'comment' and report['comment_id']:
            execute_query(
                "UPDATE comment SET status = 'blocked' WHERE id = %s",
                (report['comment_id'],)
            )
    
    elif data.action == 'reject':
        # 거부: 신고만 거부 처리
        new_status = 'rejected'
        post_action = 'keep'
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="올바른 처리 액션을 선택하세요 (approve/reject)"
        )
    
    # 신고 상태 업데이트
    execute_query("""
        UPDATE report
        SET status = %s,
            post_action = %s,
            processed_date = NOW(),
            processing_note = %s,
            assigned_to = %s
        WHERE id = %s
    """, (new_status, post_action, data.note, admin_user['user_id'], report_id))
    
    return {
        'success': True,
        'message': '신고가 처리되었습니다',
        'action': data.action,
        'new_status': new_status
    }


@router.get("/admin/reports/{report_id}/detail")
async def get_report_detail(request: Request, report_id: int):
    """
    신고 상세 정보 조회 (관리자 전용)
    
    Args:
        report_id: 신고 ID
    
    Returns:
        신고 상세 정보 + AI 분석 결과
    """
    require_admin(request)
    
    # 신고 정보 조회
    report = execute_query("""
        SELECT 
            r.id,
            r.report_type,
            r.board_id,
            r.comment_id,
            r.report_reason,
            r.report_detail,
            r.reported_content,
            r.status,
            r.priority,
            r.created_at,
            r.processed_date,
            r.processing_note,
            r.post_action,
            reporter.id as reporter_id,
            reporter.username as reporter_name,
            b.title as board_title,
            b.content as board_content,
            b.category as board_category,
            b.created_at as board_created_at,
            b.status as board_status,
            b.user_id as board_author_id,
            board_author.username as board_author_name,
            c.content as comment_content,
            c.board_id as comment_board_id,
            c.created_at as comment_created_at,
            c.status as comment_status,
            c.user_id as comment_author_id,
            comment_author.username as comment_author_name
        FROM report r
        LEFT JOIN users reporter ON r.reporter_id = reporter.id
        LEFT JOIN board b ON r.board_id = b.id
        LEFT JOIN users board_author ON b.user_id = board_author.id
        LEFT JOIN comment c ON r.comment_id = c.id
        LEFT JOIN users comment_author ON c.user_id = comment_author.id
        WHERE r.id = %s
    """, (report_id,), fetch_one=True)
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="신고를 찾을 수 없습니다"
        )
    
    # AI 분석 결과 조회
    analysis = execute_query("""
        SELECT 
            id,
            result,
            confidence,
            analysis,
            created_at
        FROM report_analysis
        WHERE report_id = %s
        ORDER BY created_at DESC
        LIMIT 1
    """, (report_id,), fetch_one=True)
    
    # 결과 타입을 한글로 변환
    result_map = {
        'match': '일치',
        'partial_match': '부분일치',
        'mismatch': '불일치'
    }
    
    return {
        'success': True,
        'report': report,
        'has_analysis': bool(analysis),
        'analysis': {
            'id': analysis['id'],
            'result': analysis['result'],
            'result_text': result_map.get(analysis['result'], analysis['result']),
            'confidence': analysis['confidence'],
            'analysis': analysis['analysis'],
            'created_at': analysis['created_at'].isoformat() if analysis['created_at'] else None
        } if analysis else None
    }


@router.get("/admin/reports/{report_id}/analysis")
async def get_report_analysis(request: Request, report_id: int):
    """
    신고 분석 결과 조회 (관리자 전용)
    
    Args:
        report_id: 신고 ID
    
    Returns:
        분석 결과 (result, confidence, analysis)
    """
    require_admin(request)
    
    # 신고 존재 확인
    report = execute_query(
        "SELECT id FROM report WHERE id = %s",
        (report_id,),
        fetch_one=True
    )
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="신고를 찾을 수 없습니다"
        )
    
    # 분석 결과 조회
    analysis = execute_query("""
        SELECT 
            id,
            result,
            confidence,
            analysis,
            created_at
        FROM report_analysis
        WHERE report_id = %s
        ORDER BY created_at DESC
        LIMIT 1
    """, (report_id,), fetch_one=True)
    
    if not analysis:
        return {
            'success': True,
            'has_analysis': False,
            'message': '아직 분석이 완료되지 않았습니다'
        }
    
    # 결과 타입을 한글로 변환
    result_map = {
        'match': '일치',
        'partial_match': '부분일치',
        'mismatch': '불일치'
    }
    
    return {
        'success': True,
        'has_analysis': True,
        'analysis': {
            'id': analysis['id'],
            'result': analysis['result'],
            'result_text': result_map.get(analysis['result'], analysis['result']),
            'confidence': analysis['confidence'],
            'analysis': analysis['analysis'],
            'created_at': analysis['created_at'].isoformat() if analysis['created_at'] else None
        }
    }

