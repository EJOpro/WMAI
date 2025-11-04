"""
게시판 API 라우터
게시글 및 댓글 CRUD 기능 제공
"""
from fastapi import APIRouter, Request, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List, Tuple
from datetime import datetime
from app.auth import get_current_user
from app.database import execute_query, get_db_connection
import pymysql
import asyncio
from concurrent.futures import ThreadPoolExecutor

router = APIRouter(tags=["board"])

# 백그라운드 작업용 executor
background_executor = ThreadPoolExecutor(max_workers=4)

# Ethics 분석 관련 import
try:
    from ethics.ethics_hybrid_predictor import HybridEthicsAnalyzer
    from ethics.ethics_db_logger import db_logger
    ETHICS_AVAILABLE = True
except ImportError as e:
    print(f"[WARN] Ethics 모듈 import 실패: {e}")
    ETHICS_AVAILABLE = False

# 전역 analyzer 인스턴스
ethics_analyzer = None


def get_ethics_analyzer():
    """Ethics analyzer 싱글톤 패턴"""
    global ethics_analyzer
    if not ETHICS_AVAILABLE:
        return None
    
    if ethics_analyzer is None:
        try:
            ethics_analyzer = HybridEthicsAnalyzer()
            print("[INFO] Ethics analyzer 초기화 완료")
        except Exception as e:
            print(f"[ERROR] Ethics analyzer 초기화 실패: {e}")
            return None
    return ethics_analyzer


def should_block_content(result: dict) -> Tuple[bool, str]:
    """
    분석 결과를 바탕으로 차단 여부 결정
    
    Returns:
        (차단여부, 차단사유)
    """
    final_score = result.get('final_score', 0)
    final_confidence = result.get('final_confidence', 0)
    spam_score = result.get('spam_score', 0)
    spam_confidence = result.get('spam_confidence', 0)
    
    # 차단 기준 1: 비윤리 점수 >= 80 AND 신뢰도 >= 80
    if final_score >= 80 and final_confidence >= 80:
        return True, "부적절한 내용이 포함되어 있습니다"
    
    # 차단 기준 2: 스팸 점수 >= 70 AND 신뢰도 >= 70
    if spam_score >= 70 and spam_confidence >= 70:
        return True, "스팸으로 의심되는 내용이 포함되어 있습니다"
    
    return False, ""


async def analyze_and_log_content(text: str, ip_address: str = None) -> Tuple[str, dict, str]:
    """
    콘텐츠 분석 및 로그 저장
    
    Returns:
        (status, result, block_reason)
    """
    try:
        analyzer = get_ethics_analyzer()
        if analyzer is None:
            print("[WARN] Ethics analyzer 없음 - 분석 건너뜀")
            return 'exposed', None, ""
        
        # 분석 실행
        result = analyzer.analyze(text)
        
        # 차단 여부 결정
        should_block, block_reason = should_block_content(result)
        status = 'blocked' if should_block else 'exposed'
        
        # 로그 저장 (ethics_logs 테이블)
        try:
            db_logger.log_analysis(
                text=text,
                score=result['final_score'],
                confidence=result['final_confidence'],
                spam=result['spam_score'],
                spam_confidence=result['spam_confidence'],
                types=result.get('types', []),
                ip_address=ip_address
            )
            print(f"[INFO] Ethics 분석 완료 - status: {status}, 비윤리: {result['final_score']:.1f}, 스팸: {result['spam_score']:.1f}")
        except Exception as log_error:
            print(f"[WARN] 로그 저장 실패: {log_error}")
        
        return status, result, block_reason
        
    except Exception as e:
        print(f"[ERROR] Ethics 분석 실패: {e}")
        return 'exposed', None, ""  # 분석 실패 시 일단 노출


def analyze_and_update_post(post_id: int, text: str, ip_address: str = None):
    """
    백그라운드에서 게시글 분석 및 상태 업데이트
    
    Args:
        post_id: 게시글 ID
        text: 분석할 텍스트
        ip_address: IP 주소
    """
    try:
        analyzer = get_ethics_analyzer()
        if analyzer is None:
            print(f"[WARN] 게시글 {post_id} - Analyzer 없음, 백그라운드 분석 건너뜀")
            return
        
        # 분석 실행
        result = analyzer.analyze(text)
        
        # 차단 여부 결정
        should_block, block_reason = should_block_content(result)
        status = 'blocked' if should_block else 'exposed'
        
        # 게시글 상태 업데이트
        execute_query(
            "UPDATE board SET status = %s WHERE id = %s",
            (status, post_id)
        )
        
        # 로그 저장
        try:
            db_logger.log_analysis(
                text=text,
                score=result['final_score'],
                confidence=result['final_confidence'],
                spam=result['spam_score'],
                spam_confidence=result['spam_confidence'],
                types=result.get('types', []),
                ip_address=ip_address
            )
        except Exception as log_error:
            print(f"[WARN] 게시글 {post_id} - 로그 저장 실패: {log_error}")
        
        print(f"[INFO] 백그라운드 분석 완료 - post_id: {post_id}, status: {status}, 비윤리: {result['final_score']:.1f}, 스팸: {result['spam_score']:.1f}")
        
    except Exception as e:
        print(f"[ERROR] 게시글 {post_id} - 백그라운드 분석 실패: {e}")


def analyze_and_update_comment(comment_id: int, text: str, ip_address: str = None):
    """
    백그라운드에서 댓글 분석 및 상태 업데이트
    
    Args:
        comment_id: 댓글 ID
        text: 분석할 텍스트
        ip_address: IP 주소
    """
    try:
        analyzer = get_ethics_analyzer()
        if analyzer is None:
            print(f"[WARN] 댓글 {comment_id} - Analyzer 없음, 백그라운드 분석 건너뜀")
            return
        
        # 분석 실행
        result = analyzer.analyze(text)
        
        # 차단 여부 결정
        should_block, block_reason = should_block_content(result)
        status = 'blocked' if should_block else 'exposed'
        
        # 댓글 상태 업데이트
        execute_query(
            "UPDATE comment SET status = %s WHERE id = %s",
            (status, comment_id)
        )
        
        # 로그 저장
        try:
            db_logger.log_analysis(
                text=text,
                score=result['final_score'],
                confidence=result['final_confidence'],
                spam=result['spam_score'],
                spam_confidence=result['spam_confidence'],
                types=result.get('types', []),
                ip_address=ip_address
            )
        except Exception as log_error:
            print(f"[WARN] 댓글 {comment_id} - 로그 저장 실패: {log_error}")
        
        print(f"[INFO] 백그라운드 분석 완료 - comment_id: {comment_id}, status: {status}, 비윤리: {result['final_score']:.1f}, 스팸: {result['spam_score']:.1f}")
        
    except Exception as e:
        print(f"[ERROR] 댓글 {comment_id} - 백그라운드 분석 실패: {e}")


class PostCreate(BaseModel):
    title: str
    content: str
    category: str = "free"


class PostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None


class CommentCreate(BaseModel):
    content: str
    parent_id: Optional[int] = None


class CommentUpdate(BaseModel):
    content: str


@router.get("/board/posts")
async def get_posts(
    request: Request,
    category: Optional[str] = None,
    page: int = 1,
    limit: int = 20
):
    """
    게시글 목록 조회
    
    Query Params:
        category: 카테고리 필터 (선택)
        page: 페이지 번호 (기본 1)
        limit: 페이지당 게시글 수 (기본 20)
    """
    offset = (page - 1) * limit
    
    # 기본 쿼리 (LEFT JOIN으로 탈퇴한 사용자 처리)
    query = """
        SELECT 
            b.id, b.title, b.content, b.category, b.status,
            b.like_count, b.view_count, b.created_at, b.updated_at,
            u.id as user_id, COALESCE(u.username, '탈퇴한 사용자') as username
        FROM board b
        LEFT JOIN users u ON b.user_id = u.id
        WHERE b.status = 'exposed'
    """
    params = []
    
    # 카테고리 필터
    if category:
        query += " AND b.category = %s"
        params.append(category)
    
    query += " ORDER BY b.created_at DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])
    
    posts = execute_query(query, tuple(params), fetch_all=True)
    
    # 전체 개수 조회
    count_query = "SELECT COUNT(*) as total FROM board WHERE status = 'exposed'"
    count_params = []
    if category:
        count_query += " AND category = %s"
        count_params.append(category)
    
    total_result = execute_query(count_query, tuple(count_params) if count_params else (), fetch_one=True)
    total = total_result['total'] if total_result else 0
    
    # 결과 포맷팅
    formatted_posts = []
    for post in posts:
        formatted_posts.append({
            'id': post['id'],
            'title': post['title'],
            'content': post['content'][:200],  # 미리보기용 200자
            'category': post['category'],
            'like_count': post['like_count'],
            'view_count': post['view_count'],
            'created_at': post['created_at'].isoformat() if post['created_at'] else None,
            'updated_at': post['updated_at'].isoformat() if post['updated_at'] else None,
            'author': {
                'id': post['user_id'],
                'username': post['username']
            }
        })
    
    return {
        'success': True,
        'posts': formatted_posts,
        'pagination': {
            'page': page,
            'limit': limit,
            'total': total,
            'total_pages': (total + limit - 1) // limit
        }
    }


@router.get("/board/posts/{post_id}")
async def get_post(request: Request, post_id: int):
    """게시글 상세 조회 (조회수 증가)"""
    
    # 조회수 증가
    execute_query(
        "UPDATE board SET view_count = view_count + 1 WHERE id = %s",
        (post_id,)
    )
    
    # 게시글 조회 (LEFT JOIN으로 탈퇴한 사용자 처리)
    post = execute_query("""
        SELECT 
            b.id, b.title, b.content, b.category, b.status,
            b.like_count, b.view_count, b.created_at, b.updated_at,
            u.id as user_id, COALESCE(u.username, '탈퇴한 사용자') as username
        FROM board b
        LEFT JOIN users u ON b.user_id = u.id
        WHERE b.id = %s AND b.status = 'exposed'
    """, (post_id,), fetch_one=True)
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="게시글을 찾을 수 없습니다"
        )
    
    # 댓글 조회 (LEFT JOIN으로 탈퇴한 사용자 처리)
    comments = execute_query("""
        SELECT 
            c.id, c.content, c.parent_id, c.status,
            c.created_at, c.updated_at,
            u.id as user_id, COALESCE(u.username, '탈퇴한 사용자') as username
        FROM comment c
        LEFT JOIN users u ON c.user_id = u.id
        WHERE c.board_id = %s AND c.status = 'exposed'
        ORDER BY c.parent_id IS NULL DESC, c.parent_id, c.created_at
    """, (post_id,), fetch_all=True)
    
    # 댓글 트리 구조 생성
    comment_map = {}
    root_comments = []
    
    for comment in comments:
        comment_obj = {
            'id': comment['id'],
            'content': comment['content'],
            'parent_id': comment['parent_id'],
            'created_at': comment['created_at'].isoformat() if comment['created_at'] else None,
            'updated_at': comment['updated_at'].isoformat() if comment['updated_at'] else None,
            'author': {
                'id': comment['user_id'],
                'username': comment['username']
            },
            'replies': []
        }
        comment_map[comment['id']] = comment_obj
        
        if comment['parent_id'] is None:
            root_comments.append(comment_obj)
        else:
            if comment['parent_id'] in comment_map:
                comment_map[comment['parent_id']]['replies'].append(comment_obj)
    
    # 현재 사용자 확인 (user_id가 NULL이면 탈퇴한 사용자이므로 is_author는 False)
    current_user = get_current_user(request)
    is_author = current_user and post['user_id'] and current_user['user_id'] == post['user_id']
    
    return {
        'success': True,
        'post': {
            'id': post['id'],
            'title': post['title'],
            'content': post['content'],
            'category': post['category'],
            'like_count': post['like_count'],
            'view_count': post['view_count'],
            'created_at': post['created_at'].isoformat() if post['created_at'] else None,
            'updated_at': post['updated_at'].isoformat() if post['updated_at'] else None,
            'author': {
                'id': post['user_id'],
                'username': post['username']
            },
            'is_author': is_author
        },
        'comments': root_comments
    }


@router.post("/board/posts")
async def create_post(request: Request, data: PostCreate):
    """게시글 작성 (로그인 필요)"""
    
    # 인증 확인
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="로그인이 필요합니다"
        )
    
    # 입력 검증
    if not data.title or len(data.title) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="제목은 2자 이상이어야 합니다"
        )
    
    if not data.content or len(data.content) < 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="내용은 5자 이상이어야 합니다"
        )
    
    # 비윤리/스팸 자동 분석 (동기 방식)
    content_text = f"{data.title}\n{data.content}"
    client_ip = request.client.host if request.client else None
    content_status, analysis_result, block_reason = await analyze_and_log_content(content_text, client_ip)
    
    # 게시글 생성 (분석된 status로 저장)
    post_id = execute_query("""
        INSERT INTO board (user_id, title, content, category, status)
        VALUES (%s, %s, %s, %s, %s)
    """, (user['user_id'], data.title, data.content, data.category, content_status))
    
    # 응답 메시지
    if content_status == 'blocked':
        return {
            'success': False,
            'message': f'게시글이 자동 차단되었습니다: {block_reason}',
            'blocked': True,
            'reason': block_reason
        }
    
    return {
        'success': True,
        'message': '게시글이 작성되었습니다',
        'post_id': post_id
    }


@router.get("/board/posts/{post_id}/status")
async def check_post_status(request: Request, post_id: int):
    """
    게시글 상태 확인 (분석 결과 확인용)
    작성자만 자신의 게시글 상태 확인 가능
    """
    # 인증 확인
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="로그인이 필요합니다"
        )
    
    # 게시글 조회 (모든 상태 포함)
    post = execute_query("""
        SELECT id, user_id, title, status
        FROM board
        WHERE id = %s
    """, (post_id,), fetch_one=True)
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="게시글을 찾을 수 없습니다"
        )
    
    # 작성자 확인
    if post['user_id'] != user['user_id']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="본인의 게시글만 확인할 수 있습니다"
        )
    
    return {
        'success': True,
        'post_id': post['id'],
        'status': post['status'],
        'title': post['title']
    }


@router.put("/board/posts/{post_id}")
async def update_post(request: Request, post_id: int, data: PostUpdate):
    """게시글 수정 (작성자만)"""
    
    # 인증 확인
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="로그인이 필요합니다"
        )
    
    # 게시글 조회
    post = execute_query(
        "SELECT user_id FROM board WHERE id = %s AND status = 'exposed'",
        (post_id,),
        fetch_one=True
    )
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="게시글을 찾을 수 없습니다"
        )
    
    # 작성자 확인
    if post['user_id'] != user['user_id']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="게시글을 수정할 권한이 없습니다"
        )
    
    # 업데이트할 필드 수집
    update_fields = []
    params = []
    
    if data.title is not None:
        if len(data.title) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="제목은 2자 이상이어야 합니다"
            )
        update_fields.append("title = %s")
        params.append(data.title)
    
    if data.content is not None:
        if len(data.content) < 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="내용은 5자 이상이어야 합니다"
            )
        update_fields.append("content = %s")
        params.append(data.content)
    
    if data.category is not None:
        update_fields.append("category = %s")
        params.append(data.category)
    
    if not update_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="수정할 내용이 없습니다"
        )
    
    # 업데이트 실행
    params.append(post_id)
    query = f"UPDATE board SET {', '.join(update_fields)} WHERE id = %s"
    execute_query(query, tuple(params))
    
    return {
        'success': True,
        'message': '게시글이 수정되었습니다'
    }


@router.delete("/board/posts/{post_id}")
async def delete_post(request: Request, post_id: int):
    """게시글 삭제 (작성자만) - soft delete"""
    
    # 인증 확인
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="로그인이 필요합니다"
        )
    
    # 게시글 조회
    post = execute_query(
        "SELECT user_id FROM board WHERE id = %s AND status != 'deleted'",
        (post_id,),
        fetch_one=True
    )
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="게시글을 찾을 수 없습니다"
        )
    
    # 작성자 확인
    if post['user_id'] != user['user_id']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="게시글을 삭제할 권한이 없습니다"
        )
    
    # Soft delete
    execute_query(
        "UPDATE board SET status = 'deleted' WHERE id = %s",
        (post_id,)
    )
    
    return {
        'success': True,
        'message': '게시글이 삭제되었습니다'
    }


@router.post("/board/posts/{post_id}/like")
async def toggle_like(request: Request, post_id: int):
    """좋아요 토글 (로그인 필요)"""
    
    # 인증 확인
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="로그인이 필요합니다"
        )
    
    # 게시글 존재 확인
    post = execute_query(
        "SELECT like_count FROM board WHERE id = %s AND status = 'exposed'",
        (post_id,),
        fetch_one=True
    )
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="게시글을 찾을 수 없습니다"
        )
    
    # 좋아요 증가 (간단한 버전 - 실제로는 별도 테이블로 관리)
    execute_query(
        "UPDATE board SET like_count = like_count + 1 WHERE id = %s",
        (post_id,)
    )
    
    return {
        'success': True,
        'message': '좋아요가 반영되었습니다',
        'like_count': post['like_count'] + 1
    }


# ===== 댓글 API =====

@router.post("/board/posts/{post_id}/comments")
async def create_comment(request: Request, post_id: int, data: CommentCreate):
    """댓글 작성 (로그인 필요)"""
    
    # 인증 확인
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="로그인이 필요합니다"
        )
    
    # 게시글 존재 확인
    post = execute_query(
        "SELECT id FROM board WHERE id = %s AND status = 'exposed'",
        (post_id,),
        fetch_one=True
    )
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="게시글을 찾을 수 없습니다"
        )
    
    # 입력 검증
    if not data.content or len(data.content) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="댓글은 2자 이상이어야 합니다"
        )
    
    # 대댓글인 경우 부모 댓글 확인
    if data.parent_id:
        parent = execute_query(
            "SELECT id FROM comment WHERE id = %s AND board_id = %s AND status = 'exposed'",
            (data.parent_id, post_id),
            fetch_one=True
        )
        
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="부모 댓글을 찾을 수 없습니다"
            )
    
    # 비윤리/스팸 자동 분석 (동기 방식)
    client_ip = request.client.host if request.client else None
    content_status, analysis_result, block_reason = await analyze_and_log_content(data.content, client_ip)
    
    # 댓글 생성 (분석된 status로 저장)
    comment_id = execute_query("""
        INSERT INTO comment (board_id, user_id, content, parent_id, status)
        VALUES (%s, %s, %s, %s, %s)
    """, (post_id, user['user_id'], data.content, data.parent_id, content_status))
    
    # 응답 메시지
    if content_status == 'blocked':
        return {
            'success': False,
            'message': f'댓글이 자동 차단되었습니다: {block_reason}',
            'blocked': True,
            'reason': block_reason
        }
    
    return {
        'success': True,
        'message': '댓글이 작성되었습니다',
        'comment_id': comment_id
    }


@router.get("/board/comments/{comment_id}/status")
async def check_comment_status(request: Request, comment_id: int):
    """
    댓글 상태 확인 (분석 결과 확인용)
    작성자만 자신의 댓글 상태 확인 가능
    """
    # 인증 확인
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="로그인이 필요합니다"
        )
    
    # 댓글 조회 (모든 상태 포함)
    comment = execute_query("""
        SELECT id, user_id, content, status
        FROM comment
        WHERE id = %s
    """, (comment_id,), fetch_one=True)
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="댓글을 찾을 수 없습니다"
        )
    
    # 작성자 확인
    if comment['user_id'] != user['user_id']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="본인의 댓글만 확인할 수 있습니다"
        )
    
    return {
        'success': True,
        'comment_id': comment['id'],
        'status': comment['status'],
        'content': comment['content']
    }


@router.put("/board/comments/{comment_id}")
async def update_comment(request: Request, comment_id: int, data: CommentUpdate):
    """댓글 수정 (작성자만)"""
    
    # 인증 확인
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="로그인이 필요합니다"
        )
    
    # 댓글 조회
    comment = execute_query(
        "SELECT user_id FROM comment WHERE id = %s AND status = 'exposed'",
        (comment_id,),
        fetch_one=True
    )
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="댓글을 찾을 수 없습니다"
        )
    
    # 작성자 확인
    if comment['user_id'] != user['user_id']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="댓글을 수정할 권한이 없습니다"
        )
    
    # 입력 검증
    if not data.content or len(data.content) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="댓글은 2자 이상이어야 합니다"
        )
    
    # 댓글 수정
    execute_query(
        "UPDATE comment SET content = %s WHERE id = %s",
        (data.content, comment_id)
    )
    
    return {
        'success': True,
        'message': '댓글이 수정되었습니다'
    }


@router.delete("/board/comments/{comment_id}")
async def delete_comment(request: Request, comment_id: int):
    """댓글 삭제 (작성자만) - soft delete"""
    
    # 인증 확인
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="로그인이 필요합니다"
        )
    
    # 댓글 조회
    comment = execute_query(
        "SELECT user_id FROM comment WHERE id = %s AND status != 'deleted'",
        (comment_id,),
        fetch_one=True
    )
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="댓글을 찾을 수 없습니다"
        )
    
    # 작성자 확인
    if comment['user_id'] != user['user_id']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="댓글을 삭제할 권한이 없습니다"
        )
    
    # Soft delete
    execute_query(
        "UPDATE comment SET status = 'deleted' WHERE id = %s",
        (comment_id,)
    )
    
    return {
        'success': True,
        'message': '댓글이 삭제되었습니다'
    }


@router.get("/board/categories")
async def get_categories():
    """사용 가능한 카테고리 목록"""
    categories = [
        {'value': 'free', 'label': '자유게시판'},
        {'value': 'notice', 'label': '공지사항'},
        {'value': 'qna', 'label': '질문답변'},
        {'value': 'review', 'label': '후기'},
        {'value': 'tips', 'label': '팁/노하우'},
    ]
    
    return {
        'success': True,
        'categories': categories
    }


# ===== 신고 API =====

class ReportCreate(BaseModel):
    """신고 생성 모델"""
    reason: str  # '욕설 및 비방', '도배 및 광고', '사생활 침해', '저작권 침해'
    detail: Optional[str] = None  # 상세 사유 (선택)


@router.post("/board/posts/{post_id}/report")
async def report_post(request: Request, post_id: int, data: ReportCreate):
    """게시글 신고 (로그인 필요)"""
    
    # 인증 확인
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="로그인이 필요합니다"
        )
    
    # 게시글 존재 확인
    post = execute_query(
        "SELECT id, user_id, title, content FROM board WHERE id = %s AND status = 'exposed'",
        (post_id,),
        fetch_one=True
    )
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="게시글을 찾을 수 없습니다"
        )
    
    # 자기 게시글은 신고 불가
    if post['user_id'] and post['user_id'] == user['user_id']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="자신의 게시글은 신고할 수 없습니다"
        )
    
    # 신고 사유 검증
    valid_reasons = ['욕설 및 비방', '도배 및 광고', '사생활 침해', '저작권 침해']
    if data.reason not in valid_reasons:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"올바른 신고 사유를 선택해주세요: {', '.join(valid_reasons)}"
        )
    
    # 중복 신고 확인 (같은 사용자가 같은 게시글을 이미 신고했는지)
    existing_report = execute_query("""
        SELECT id FROM report 
        WHERE reporter_id = %s 
        AND board_id = %s 
        AND status = 'pending'
    """, (user['user_id'], post_id), fetch_one=True)
    
    if existing_report:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 신고한 게시글입니다"
        )
    
    # 신고 내용 생성 (게시글 정보 저장)
    reported_content = f"[제목] {post['title']}\n[내용] {post['content'][:200]}{'...' if len(post['content']) > 200 else ''}"
    
    # 신고 생성
    report_id = execute_query("""
        INSERT INTO report 
        (report_type, board_id, reported_content, report_reason, report_detail, reporter_id, status, priority)
        VALUES ('board', %s, %s, %s, %s, %s, 'pending', 'normal')
    """, (post_id, reported_content, data.reason, data.detail, user['user_id']))
    
    return {
        'success': True,
        'message': '신고가 접수되었습니다. 검토 후 조치하겠습니다.',
        'report_id': report_id
    }


@router.get("/board/posts/{post_id}/report/check")
async def check_report_status(request: Request, post_id: int):
    """게시글 신고 여부 확인 (로그인 필요)"""
    
    user = get_current_user(request)
    if not user:
        return {'reported': False}
    
    # 사용자가 이 게시글을 신고했는지 확인
    report = execute_query("""
        SELECT id, report_reason, status 
        FROM report 
        WHERE reporter_id = %s AND board_id = %s AND status = 'pending'
    """, (user['user_id'], post_id), fetch_one=True)
    
    return {
        'reported': bool(report),
        'report_reason': report['report_reason'] if report else None,
        'report_id': report['id'] if report else None
    }


@router.post("/board/comments/{comment_id}/report")
async def report_comment(request: Request, comment_id: int, data: ReportCreate):
    """댓글 신고 (로그인 필요)"""
    
    # 인증 확인
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="로그인이 필요합니다"
        )
    
    # 댓글 존재 확인
    comment = execute_query(
        "SELECT id, user_id, content, board_id FROM comment WHERE id = %s AND status = 'exposed'",
        (comment_id,),
        fetch_one=True
    )
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="댓글을 찾을 수 없습니다"
        )
    
    # 자기 댓글은 신고 불가
    if comment['user_id'] and comment['user_id'] == user['user_id']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="자신의 댓글은 신고할 수 없습니다"
        )
    
    # 신고 사유 검증
    valid_reasons = ['욕설 및 비방', '도배 및 광고', '사생활 침해', '저작권 침해']
    if data.reason not in valid_reasons:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"올바른 신고 사유를 선택해주세요: {', '.join(valid_reasons)}"
        )
    
    # 중복 신고 확인 (같은 사용자가 같은 댓글을 이미 신고했는지)
    existing_report = execute_query("""
        SELECT id FROM report 
        WHERE reporter_id = %s 
        AND comment_id = %s 
        AND status = 'pending'
    """, (user['user_id'], comment_id), fetch_one=True)
    
    if existing_report:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 신고한 댓글입니다"
        )
    
    # 신고 내용 생성 (댓글 정보 저장)
    reported_content = f"[댓글] {comment['content'][:200]}{'...' if len(comment['content']) > 200 else ''}"
    
    # 신고 생성
    report_id = execute_query("""
        INSERT INTO report 
        (report_type, comment_id, reported_content, report_reason, report_detail, reporter_id, status, priority)
        VALUES ('comment', %s, %s, %s, %s, %s, 'pending', 'normal')
    """, (comment_id, reported_content, data.reason, data.detail, user['user_id']))
    
    return {
        'success': True,
        'message': '신고가 접수되었습니다. 검토 후 조치하겠습니다.',
        'report_id': report_id
    }


@router.get("/board/comments/{comment_id}/report/check")
async def check_comment_report_status(request: Request, comment_id: int):
    """댓글 신고 여부 확인 (로그인 필요)"""
    
    user = get_current_user(request)
    if not user:
        return {'reported': False}
    
    # 사용자가 이 댓글을 신고했는지 확인
    report = execute_query("""
        SELECT id, report_reason, status 
        FROM report 
        WHERE reporter_id = %s AND comment_id = %s AND status = 'pending'
    """, (user['user_id'], comment_id), fetch_one=True)
    
    return {
        'reported': bool(report),
        'report_reason': report['report_reason'] if report else None,
        'report_id': report['id'] if report else None
    }

