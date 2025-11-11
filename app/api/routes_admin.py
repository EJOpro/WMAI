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


class EthicsFeedbackRequest(BaseModel):
    """Ethics 피드백 요청"""
    log_id: int
    action: str  # 'immoral', 'spam', 'clean'
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
    
    # 신고 조회 (신고 사유와 내용 포함)
    report = execute_query("""
        SELECT r.id, r.report_type, r.board_id, r.comment_id, r.status, r.report_reason,
               b.content as board_content, c.content as comment_content
        FROM report r
        LEFT JOIN board b ON r.board_id = b.id
        LEFT JOIN comment c ON r.comment_id = c.id
        WHERE r.id = %s
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
    
    # 관리자 확정 사례에 추가
    try:
        report_reason = report.get('report_reason', '')
        content = report.get('board_content') or report.get('comment_content', '')
        
        # 신고 사유와 처리 액션에 따른 확정 타입 결정
        admin_action = None
        
        if report_reason == '욕설 및 비방':
            if data.action == 'approve':
                admin_action = 'immoral'  # 비윤리 확정
            elif data.action == 'reject':
                admin_action = 'clean'  # 문제없음 확정
        
        elif report_reason == '도배 및 광고':
            if data.action == 'approve':
                admin_action = 'spam'  # 스팸 확정
            elif data.action == 'reject':
                admin_action = 'clean'  # 문제없음 확정
        
        # 확정 사례 저장 (내용이 10자 이상이고 admin_action이 결정된 경우만)
        if admin_action and content and len(content.strip()) >= 10:
            from ethics.ethics_feedback import save_feedback_to_vector_db
            from ethics.ethics_db_logger import DatabaseLogger
            
            # 해당 콘텐츠의 ethics_logs 조회 (최근 로그)
            db_logger = DatabaseLogger()
            logs = db_logger.get_logs(limit=1, offset=0)
            
            # 기본 점수 설정 (로그가 없는 경우)
            original_immoral_score = 50.0
            original_spam_score = 50.0
            original_immoral_confidence = 50.0
            original_spam_confidence = 50.0
            
            # 콘텐츠와 일치하는 로그 찾기
            for log in logs:
                if log.get('text') == content:
                    original_immoral_score = float(log.get('score', 50.0))
                    original_spam_score = float(log.get('spam', 50.0))
                    original_immoral_confidence = float(log.get('confidence', 50.0))
                    original_spam_confidence = float(log.get('spam_confidence', 50.0))
                    break
            
            # VectorDB에 저장
            save_feedback_to_vector_db(
                text=content,
                original_immoral_score=original_immoral_score,
                original_spam_score=original_spam_score,
                original_immoral_confidence=original_immoral_confidence,
                original_spam_confidence=original_spam_confidence,
                admin_action=admin_action,
                admin_id=admin_user['user_id'],
                log_id=report_id,
                note=f"신고처리: {report_reason} - {data.action}"
            )
            
            print(f"[INFO] 신고 처리 후 관리자 확정 사례 저장: report_id={report_id}, action={admin_action}")
    
    except Exception as e:
        # 확정 사례 저장 실패해도 신고 처리는 계속 진행
        print(f"[WARN] 관리자 확정 사례 저장 실패: {e}")
    
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


@router.post("/admin/ethics/feedback")
async def save_ethics_feedback(request: Request, feedback_data: EthicsFeedbackRequest):
    """
    관리자가 비윤리/스팸 분석 결과에 대한 피드백 저장 (벡터DB에만)
    
    Args:
        feedback_data: 피드백 데이터
            - log_id: ethics_logs 테이블의 ID
            - action: 'immoral', 'spam', 'clean'
            - note: 관리자 메모
    
    Returns:
        저장 결과
    """
    admin_user = require_admin(request)
    
    # 기존 분석 로그 조회
    log = execute_query("""
        SELECT id, text, score, spam, confidence, spam_confidence
        FROM ethics_logs
        WHERE id = %s
    """, (feedback_data.log_id,), fetch_one=True)
    
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="분석 로그를 찾을 수 없습니다"
        )
    
    # 액션 검증
    if feedback_data.action not in ['immoral', 'spam', 'clean']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="올바른 액션을 선택하세요 (immoral/spam/clean)"
        )
    
    # 벡터DB에 피드백 저장
    try:
        from ethics.ethics_feedback import save_feedback_to_vector_db
        
        save_feedback_to_vector_db(
            text=log['text'],
            original_immoral_score=log['score'],
            original_spam_score=log['spam'],
            original_immoral_confidence=log['confidence'],
            original_spam_confidence=log['spam_confidence'],
            admin_action=feedback_data.action,
            admin_id=admin_user['user_id'],
            log_id=feedback_data.log_id,
            note=feedback_data.note
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"피드백 저장 실패: {str(e)}"
        )
    
    # ethics_logs 테이블 업데이트 (관리자 확정 정보 저장)
    try:
        from datetime import datetime
        execute_query("""
            UPDATE ethics_logs
            SET admin_confirmed = 1,
                confirmed_type = %s,
                confirmed_at = %s,
                confirmed_by = %s
            WHERE id = %s
        """, (feedback_data.action, datetime.now(), admin_user['user_id'], feedback_data.log_id))
    except Exception as e:
        print(f"[WARN] ethics_logs 업데이트 실패: {e}")
        # 로그 업데이트 실패해도 피드백은 이미 저장되었으므로 계속 진행
    
    return {
        'success': True,
        'message': '피드백이 저장되었습니다',
        'action': feedback_data.action
    }


@router.delete("/admin/ethics/feedback/{case_id}")
async def delete_ethics_feedback_case(request: Request, case_id: str):
    """관리자 확정 사례 삭제"""
    require_admin(request)
    
    try:
        from ethics.ethics_vector_db import get_client, delete_case
        client = get_client()
        result = delete_case(client=client, chunk_id=case_id)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="확정 사례를 찾을 수 없습니다."
            )
        
        return {
            'success': True,
            'deleted_id': case_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"삭제 중 오류: {str(e)}"
        )


@router.get("/admin/ethics/all-cases")
async def list_all_vector_cases(
    request: Request,
    limit: int = 20,
    offset: int = 0
):
    """벡터DB 전체 사례 목록 조회"""
    require_admin(request)

    if limit < 1:
        limit = 1
    limit = min(limit, 100)
    offset = max(offset, 0)

    try:
        from ethics.ethics_vector_db import get_client, get_all_cases
        client = get_client()
        cases = get_all_cases(
            client=client,
            limit=limit,
            offset=offset
        )

        from datetime import datetime

        case_list = []
        for case in cases:
            metadata = case.get('metadata', {}) or {}
            created_at_raw = metadata.get('created_at')
            
            immoral_score = float(metadata.get('immoral_score', 0.0) or 0.0)
            spam_score = float(metadata.get('spam_score', 0.0) or 0.0)
            immoral_confidence = float(metadata.get('immoral_confidence', metadata.get('confidence', 0.0)) or 0.0)
            spam_confidence = float(metadata.get('spam_confidence', 0.0) or 0.0)
            confirmed = metadata.get('confirmed', False)

            created_at_iso = None
            if created_at_raw:
                try:
                    normalized = created_at_raw
                    if len(normalized) == 19 and 'T' not in normalized:
                        normalized = normalized.replace(' ', 'T')
                    if not (normalized.endswith('Z') or ('+' in normalized and len(normalized.split('+')[-1]) in [4,5])):
                        normalized += '+00:00'
                    created_at_iso = datetime.fromisoformat(normalized).isoformat()
                except ValueError:
                    pass

            case_list.append({
                'id': case.get('id'),
                'text': case.get('document') or metadata.get('sentence', ''),
                'created_at': created_at_iso,
                'immoral_score': immoral_score,
                'spam_score': spam_score,
                'immoral_confidence': immoral_confidence,
                'spam_confidence': spam_confidence,
                'confirmed': confirmed,
                'post_id': metadata.get('post_id'),
                'user_id': metadata.get('user_id'),
                'feedback_type': metadata.get('feedback_type'),
                'admin_action': metadata.get('admin_action'),
                'metadata': metadata
            })

        return {
            'success': True,
            'cases': case_list,
            'count': len(case_list),
            'limit': limit,
            'offset': offset
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"사례 조회 실패: {str(e)}"
        )


@router.get("/admin/ethics/feedback")
async def list_ethics_feedback(
    request: Request,
    limit: int = 20,
    offset: int = 0,
    source_type: Optional[str] = None,
    action: Optional[str] = None
):
    """관리자 확정 사례 목록 조회 (벡터DB에서)"""
    require_admin(request)

    if limit < 1:
        limit = 1
    limit = min(limit, 100)
    offset = max(offset, 0)

    try:
        from ethics.ethics_vector_db import get_client, get_recent_confirmed_cases
        client = get_client()
        cases = get_recent_confirmed_cases(
            client=client,
            limit=limit,
            offset=offset,
            action=action,
            source_type=source_type
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"확정 사례 조회 실패: {str(e)}"
        )

    feedback_list = []
    for case in cases:
        metadata = case.get('metadata', {}) or {}
        created_at_raw = metadata.get('created_at')
        source = metadata.get('source_type', 'ethics_log')
        admin_action = metadata.get('admin_action')

        created_at_iso = None
        if created_at_raw:
            try:
                normalized = created_at_raw.replace('Z', '+00:00')
                created_at_iso = datetime.fromisoformat(normalized).isoformat()
            except Exception:
                created_at_iso = created_at_raw

        feedback_list.append({
            'id': case.get('id'),
            'text': case.get('document') or metadata.get('sentence', ''),
            'created_at': created_at_iso,
            'admin_action': admin_action,
            'confidence': metadata.get('confidence'),
            'immoral_score': metadata.get('immoral_score'),
            'spam_score': metadata.get('spam_score'),
            'note': metadata.get('note'),
            'admin_id': metadata.get('admin_id'),
            'feedback_type': metadata.get('feedback_type'),
            'source_type': source,
            'source_id': metadata.get('source_id') or metadata.get('report_id'),
            'metadata': metadata
        })

    return {
        'success': True,
        'feedbacks': feedback_list,
        'count': len(feedback_list),
        'limit': limit,
        'offset': offset
    }

 
@router.get("/admin/ethics/feedback/stats")
async def get_ethics_feedback_stats(request: Request):
    """
    피드백 통계 조회 (관리자 전용)
    
    Returns:
        피드백 통계 정보
    """
    require_admin(request)
    
    try:
        # 액션별 통계
        action_stats = execute_query("""
            SELECT 
                action,
                COUNT(*) as count,
                AVG(original_score - COALESCE(adjusted_score, original_score)) as avg_score_diff
            FROM ethics_feedback
            GROUP BY action
        """, fetch_all=True)
        
        # 전체 통계
        total_stats = execute_query("""
            SELECT 
                COUNT(*) as total_count,
                COUNT(DISTINCT log_id) as unique_logs,
                COUNT(DISTINCT admin_id) as admin_count,
                AVG(original_score - COALESCE(adjusted_score, original_score)) as overall_avg_diff
            FROM ethics_feedback
        """, fetch_one=True)
        
        return {
            'success': True,
            'action_stats': action_stats,
            'total_stats': total_stats
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"통계 조회 실패: {str(e)}"
        )


# ============================================
# 이미지 분석 로그 관리 API
# ============================================

@router.get("/admin/images/blocked")
async def get_blocked_images(
    request: Request,
    page: int = 1,
    limit: int = 20
):
    """
    차단된 이미지 목록 조회 (관리자 전용)
    
    Args:
        page: 페이지 번호
        limit: 페이지당 개수
    
    Returns:
        차단된 이미지 목록
    """
    require_admin(request)
    
    offset = (page - 1) * limit
    
    try:
        # 차단된 이미지 목록 조회
        images = execute_query("""
            SELECT * FROM v_blocked_images
            LIMIT %s OFFSET %s
        """, (limit, offset), fetch_all=True)
        
        # 총 개수 조회
        total = execute_query("""
            SELECT COUNT(*) as count
            FROM image_analysis_logs
            WHERE is_blocked = TRUE
        """, fetch_one=True)
        
        return {
            'success': True,
            'images': images,
            'pagination': {
                'total': total['count'] if total else 0,
                'page': page,
                'limit': limit,
                'total_pages': ((total['count'] if total else 0) + limit - 1) // limit
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"차단된 이미지 조회 실패: {str(e)}"
        )


@router.get("/admin/images/logs")
async def get_image_analysis_logs(
    request: Request,
    page: int = 1,
    limit: int = 50,
    blocked_only: bool = False
):
    """
    이미지 분석 로그 조회 (관리자 전용)
    
    Args:
        page: 페이지 번호
        limit: 페이지당 개수
        blocked_only: 차단된 것만 조회
    
    Returns:
        이미지 분석 로그 목록
    """
    require_admin(request)
    
    offset = (page - 1) * limit
    where_clause = "WHERE is_blocked = TRUE" if blocked_only else ""
    
    try:
        # 로그 조회
        logs = execute_query(f"""
            SELECT 
                l.*,
                b.title as board_title,
                b.user_id as uploader_id,
                u.username as uploader_name
            FROM image_analysis_logs l
            LEFT JOIN board b ON l.board_id = b.id
            LEFT JOIN users u ON b.user_id = u.id
            {where_clause}
            ORDER BY l.created_at DESC
            LIMIT %s OFFSET %s
        """, (limit, offset), fetch_all=True)
        
        # 총 개수
        total = execute_query(f"""
            SELECT COUNT(*) as count
            FROM image_analysis_logs
            {where_clause}
        """, fetch_one=True)
        
        return {
            'success': True,
            'logs': logs,
            'pagination': {
                'total': total['count'] if total else 0,
                'page': page,
                'limit': limit,
                'total_pages': ((total['count'] if total else 0) + limit - 1) // limit
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"이미지 로그 조회 실패: {str(e)}"
        )


@router.get("/admin/images/stats")
async def get_image_analysis_stats(request: Request):
    """
    이미지 분석 통계 (관리자 전용)
    
    Returns:
        이미지 분석 통계 정보
    """
    require_admin(request)
    
    try:
        # 전체 통계
        total_stats = execute_query("""
            SELECT 
                COUNT(*) as total_analyzed,
                SUM(CASE WHEN is_blocked = TRUE THEN 1 ELSE 0 END) as total_blocked,
                SUM(CASE WHEN is_nsfw = TRUE THEN 1 ELSE 0 END) as total_nsfw,
                AVG(nsfw_confidence) as avg_nsfw_confidence,
                AVG(immoral_score) as avg_immoral_score,
                AVG(spam_score) as avg_spam_score,
                AVG(response_time) as avg_response_time
            FROM image_analysis_logs
        """, fetch_one=True)
        
        # 일별 통계 (최근 7일)
        daily_stats = execute_query("""
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as total,
                SUM(CASE WHEN is_blocked = TRUE THEN 1 ELSE 0 END) as blocked
            FROM image_analysis_logs
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """, fetch_all=True)
        
        return {
            'success': True,
            'total_stats': total_stats,
            'daily_stats': daily_stats
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"이미지 통계 조회 실패: {str(e)}"
        )


@router.delete("/admin/images/logs/{log_id}")
async def delete_image_log(request: Request, log_id: int):
    """
    이미지 분석 로그 삭제 (관리자 전용)
    
    Args:
        log_id: 삭제할 로그 ID
        
    Returns:
        삭제 결과
    """
    require_admin(request)
    
    try:
        # 로그 존재 확인
        log = execute_query("""
            SELECT id, filename
            FROM image_analysis_logs
            WHERE id = %s
        """, (log_id,), fetch_one=True)
        
        if not log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="로그를 찾을 수 없습니다"
            )
        
        # 로그 삭제
        execute_query("""
            DELETE FROM image_analysis_logs
            WHERE id = %s
        """, (log_id,))
        
        return {
            'success': True,
            'message': '로그가 삭제되었습니다',
            'deleted_id': log_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"로그 삭제 실패: {str(e)}"
        )