"""
사용자 간 1:1 쪽지/DM 시스템 API 라우터
"""
from fastapi import APIRouter, Request, HTTPException, status
from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime
from app.auth import get_current_user, require_login
from app.database import execute_query
import html

router = APIRouter(tags=["messages"], prefix="/api/messages")

# 중요: 라우터 정의 순서
# 더 구체적인 경로(/inbox, /sent, /unread-count, /users/search)를
# 파라미터화된 경로(/{message_id})보다 먼저 정의해야 합니다!


class MessageCreate(BaseModel):
    """메시지 전송 요청"""
    receiver_username: str
    subject: Optional[str] = None
    content: str
    
    @validator('content')
    def content_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('메시지 내용은 필수입니다')
        if len(v) > 5000:
            raise ValueError('메시지 내용은 5000자를 초과할 수 없습니다')
        return v.strip()
    
    @validator('subject')
    def subject_length(cls, v):
        if v and len(v) > 200:
            raise ValueError('제목은 200자를 초과할 수 없습니다')
        return v.strip() if v else None


class MessageReply(BaseModel):
    """답장 요청"""
    content: str
    
    @validator('content')
    def content_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('메시지 내용은 필수입니다')
        if len(v) > 5000:
            raise ValueError('메시지 내용은 5000자를 초과할 수 없습니다')
        return v.strip()


@router.get("/inbox")
async def get_inbox(request: Request, page: int = 1, limit: int = 20):
    """
    받은 메시지함 조회
    - 수신자가 삭제하지 않은 메시지만 표시
    - 페이지네이션 지원
    """
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="로그인이 필요합니다")
    
    user_id = user['user_id']
    offset = (page - 1) * limit
    
    # 받은 메시지 조회
    messages = execute_query("""
        SELECT 
            m.id, m.subject, m.content, m.is_read, m.read_at, m.created_at,
            m.sender_id, u.username as sender_username,
            m.parent_message_id
        FROM messages m
        JOIN users u ON m.sender_id = u.id
        WHERE m.receiver_id = %s AND m.deleted_by_receiver = FALSE
        ORDER BY m.created_at DESC
        LIMIT %s OFFSET %s
    """, (user_id, limit, offset), fetch_all=True)
    
    # 총 개수
    total = execute_query("""
        SELECT COUNT(*) as count
        FROM messages
        WHERE receiver_id = %s AND deleted_by_receiver = FALSE
    """, (user_id,), fetch_one=True)
    
    total_count = total['count'] if total else 0
    total_pages = (total_count + limit - 1) // limit
    
    return {
        'messages': messages or [],
        'pagination': {
            'page': page,
            'limit': limit,
            'total': total_count,
            'total_pages': total_pages
        }
    }


@router.get("/sent")
async def get_sent_messages(request: Request, page: int = 1, limit: int = 20):
    """
    보낸 메시지함 조회
    - 발신자가 삭제하지 않은 메시지만 표시
    - 페이지네이션 지원
    """
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="로그인이 필요합니다")
    
    user_id = user['user_id']
    offset = (page - 1) * limit
    
    # 보낸 메시지 조회
    messages = execute_query("""
        SELECT 
            m.id, m.subject, m.content, m.is_read, m.read_at, m.created_at,
            m.receiver_id, u.username as receiver_username,
            m.parent_message_id
        FROM messages m
        JOIN users u ON m.receiver_id = u.id
        WHERE m.sender_id = %s AND m.deleted_by_sender = FALSE
        ORDER BY m.created_at DESC
        LIMIT %s OFFSET %s
    """, (user_id, limit, offset), fetch_all=True)
    
    # 총 개수
    total = execute_query("""
        SELECT COUNT(*) as count
        FROM messages
        WHERE sender_id = %s AND deleted_by_sender = FALSE
    """, (user_id,), fetch_one=True)
    
    total_count = total['count'] if total else 0
    total_pages = (total_count + limit - 1) // limit
    
    return {
        'messages': messages or [],
        'pagination': {
            'page': page,
            'limit': limit,
            'total': total_count,
            'total_pages': total_pages
        }
    }


@router.get("/unread-count")
async def get_unread_count(request: Request):
    """
    안읽은 메시지 개수 조회
    - 실시간 알림용
    """
    user = get_current_user(request)
    if not user:
        return {'count': 0}
    
    user_id = user['user_id']
    
    result = execute_query("""
        SELECT COUNT(*) as count
        FROM messages
        WHERE receiver_id = %s 
          AND is_read = FALSE 
          AND deleted_by_receiver = FALSE
    """, (user_id,), fetch_one=True)
    
    return {'count': result['count'] if result else 0}


@router.get("/users/search")
async def search_users(request: Request, q: str = ""):
    """
    사용자 검색 (수신자 선택용)
    - 자기 자신은 제외
    - 최대 10명까지
    """
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="로그인이 필요합니다")
    
    user_id = user['user_id']
    
    if not q or len(q.strip()) < 1:
        return {'users': []}
    
    # 사용자 검색 (자기 자신 제외)
    users = execute_query("""
        SELECT id, username
        FROM users
        WHERE username LIKE %s AND id != %s
        LIMIT 10
    """, (f"%{q}%", user_id), fetch_all=True)
    
    return {'users': users or []}


@router.get("/{message_id}")
async def get_message_detail(request: Request, message_id: int):
    """
    메시지 상세 조회
    - 수신자가 읽을 때 읽음 처리
    - 권한 검증: 발신자 또는 수신자만 조회 가능
    """
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="로그인이 필요합니다")
    
    user_id = user['user_id']
    
    # 메시지 조회
    message = execute_query("""
        SELECT 
            m.*,
            sender.username as sender_username,
            receiver.username as receiver_username
        FROM messages m
        JOIN users sender ON m.sender_id = sender.id
        JOIN users receiver ON m.receiver_id = receiver.id
        WHERE m.id = %s
    """, (message_id,), fetch_one=True)
    
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="메시지를 찾을 수 없습니다")
    
    # 권한 검증
    if message['sender_id'] != user_id and message['receiver_id'] != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="권한이 없습니다")
    
    # 수신자가 처음 읽을 때 읽음 처리
    if message['receiver_id'] == user_id and not message['is_read']:
        execute_query("""
            UPDATE messages
            SET is_read = TRUE, read_at = NOW()
            WHERE id = %s
        """, (message_id,))
        message['is_read'] = True
        message['read_at'] = datetime.now()
    
    return {'message': message}


@router.post("")
async def send_message(request: Request, data: MessageCreate):
    """
    새 메시지 전송
    - 수신자 존재 확인
    - XSS 방지를 위해 HTML 이스케이프
    """
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="로그인이 필요합니다")
    
    sender_id = user['user_id']
    
    # 수신자 조회
    receiver = execute_query("""
        SELECT id FROM users WHERE username = %s
    """, (data.receiver_username,), fetch_one=True)
    
    if not receiver:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="수신자를 찾을 수 없습니다")
    
    receiver_id = receiver['id']
    
    # 자기 자신에게 메시지 전송 방지
    if sender_id == receiver_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="자기 자신에게 메시지를 보낼 수 없습니다")
    
    # XSS 방지: HTML 이스케이프
    safe_content = html.escape(data.content)
    safe_subject = html.escape(data.subject) if data.subject else None
    
    # 메시지 저장
    message_id = execute_query("""
        INSERT INTO messages (sender_id, receiver_id, subject, content)
        VALUES (%s, %s, %s, %s)
    """, (sender_id, receiver_id, safe_subject, safe_content))
    
    return {
        'success': True,
        'message_id': message_id,
        'message': '메시지가 전송되었습니다'
    }


@router.post("/{message_id}/reply")
async def reply_message(request: Request, message_id: int, data: MessageReply):
    """
    메시지 답장
    - 원본 메시지 조회 및 권한 검증
    - 제목 자동 생성 (Re: ...)
    """
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="로그인이 필요합니다")
    
    user_id = user['user_id']
    
    # 원본 메시지 조회
    original = execute_query("""
        SELECT * FROM messages WHERE id = %s
    """, (message_id,), fetch_one=True)
    
    if not original:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="원본 메시지를 찾을 수 없습니다")
    
    # 권한 검증: 수신자만 답장 가능
    if original['receiver_id'] != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="수신자만 답장할 수 있습니다")
    
    # 답장 제목 생성
    reply_subject = original['subject'] or '(제목 없음)'
    if not reply_subject.startswith('Re: '):
        reply_subject = f"Re: {reply_subject}"
    
    # XSS 방지
    safe_content = html.escape(data.content)
    safe_subject = html.escape(reply_subject)
    
    # 답장 저장 (발신자와 수신자가 바뀜)
    new_message_id = execute_query("""
        INSERT INTO messages (sender_id, receiver_id, subject, content, parent_message_id)
        VALUES (%s, %s, %s, %s, %s)
    """, (user_id, original['sender_id'], safe_subject, safe_content, message_id))
    
    return {
        'success': True,
        'message_id': new_message_id,
        'message': '답장이 전송되었습니다'
    }


@router.delete("/{message_id}")
async def delete_message(request: Request, message_id: int):
    """
    메시지 삭제 (소프트 삭제)
    - 발신자: deleted_by_sender = TRUE
    - 수신자: deleted_by_receiver = TRUE
    - 양쪽 모두 삭제 시 물리 삭제
    """
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="로그인이 필요합니다")
    
    user_id = user['user_id']
    
    # 메시지 조회
    message = execute_query("""
        SELECT * FROM messages WHERE id = %s
    """, (message_id,), fetch_one=True)
    
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="메시지를 찾을 수 없습니다")
    
    # 권한 검증
    if message['sender_id'] != user_id and message['receiver_id'] != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="권한이 없습니다")
    
    # 발신자인지 수신자인지 확인
    if message['sender_id'] == user_id:
        # 발신자가 삭제
        if message['deleted_by_receiver']:
            # 수신자도 이미 삭제했으면 물리 삭제
            execute_query("DELETE FROM messages WHERE id = %s", (message_id,))
        else:
            # 소프트 삭제
            execute_query("UPDATE messages SET deleted_by_sender = TRUE WHERE id = %s", (message_id,))
    else:
        # 수신자가 삭제
        if message['deleted_by_sender']:
            # 발신자도 이미 삭제했으면 물리 삭제
            execute_query("DELETE FROM messages WHERE id = %s", (message_id,))
        else:
            # 소프트 삭제
            execute_query("UPDATE messages SET deleted_by_receiver = TRUE WHERE id = %s", (message_id,))
    
    return {
        'success': True,
        'message': '메시지가 삭제되었습니다'
    }

