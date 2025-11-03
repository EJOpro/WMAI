"""
게시판 API 라우터
게시글 및 댓글 CRUD 기능 제공
"""
from fastapi import APIRouter, Request, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.auth import get_current_user
from app.database import execute_query, get_db_connection
import pymysql

router = APIRouter(tags=["board"])


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
    
    # 기본 쿼리
    query = """
        SELECT 
            b.id, b.title, b.content, b.category, b.status,
            b.like_count, b.view_count, b.created_at, b.updated_at,
            u.id as user_id, u.username
        FROM board b
        JOIN users u ON b.user_id = u.id
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
    
    # 게시글 조회
    post = execute_query("""
        SELECT 
            b.id, b.title, b.content, b.category, b.status,
            b.like_count, b.view_count, b.created_at, b.updated_at,
            u.id as user_id, u.username
        FROM board b
        JOIN users u ON b.user_id = u.id
        WHERE b.id = %s AND b.status = 'exposed'
    """, (post_id,), fetch_one=True)
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="게시글을 찾을 수 없습니다"
        )
    
    # 댓글 조회
    comments = execute_query("""
        SELECT 
            c.id, c.content, c.parent_id, c.status,
            c.created_at, c.updated_at,
            u.id as user_id, u.username
        FROM comment c
        JOIN users u ON c.user_id = u.id
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
    
    # 현재 사용자 확인
    current_user = get_current_user(request)
    is_author = current_user and current_user['user_id'] == post['user_id']
    
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
    
    # 게시글 생성
    post_id = execute_query("""
        INSERT INTO board (user_id, title, content, category, status)
        VALUES (%s, %s, %s, %s, 'exposed')
    """, (user['user_id'], data.title, data.content, data.category))
    
    return {
        'success': True,
        'message': '게시글이 작성되었습니다',
        'post_id': post_id
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
    
    # 댓글 생성
    comment_id = execute_query("""
        INSERT INTO comment (board_id, user_id, content, parent_id, status)
        VALUES (%s, %s, %s, %s, 'exposed')
    """, (post_id, user['user_id'], data.content, data.parent_id))
    
    return {
        'success': True,
        'message': '댓글이 작성되었습니다',
        'comment_id': comment_id
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

