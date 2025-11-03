"""
인증 및 세션 관리
bcrypt를 사용한 비밀번호 해싱 및 FastAPI 세션 관리
"""
import bcrypt
from functools import wraps
from fastapi import Request, HTTPException, status
from typing import Optional, Dict


def hash_password(password: str) -> str:
    """
    비밀번호를 bcrypt로 해싱
    
    Args:
        password: 원본 비밀번호
    
    Returns:
        해싱된 비밀번호 문자열
    """
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(password: str, hashed_password: str) -> bool:
    """
    비밀번호 검증
    
    Args:
        password: 입력된 비밀번호
        hashed_password: 저장된 해시 비밀번호
    
    Returns:
        비밀번호 일치 여부
    """
    password_bytes = password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def get_current_user(request: Request) -> Optional[Dict]:
    """
    세션에서 현재 사용자 정보 가져오기
    
    Args:
        request: FastAPI Request 객체
    
    Returns:
        사용자 정보 딕셔너리 또는 None
    """
    user_id = request.session.get('user_id')
    username = request.session.get('username')
    role = request.session.get('role', 'user')
    
    if user_id and username:
        return {
            'user_id': user_id,
            'username': username,
            'role': role
        }
    return None


def require_login(func):
    """
    로그인 필수 데코레이터
    
    Usage:
        @require_login
        async def protected_route(request: Request):
            user = get_current_user(request)
            ...
    """
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        user = get_current_user(request)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="로그인이 필요합니다"
            )
        return await func(request, *args, **kwargs)
    return wrapper


def set_session_user(request: Request, user_id: int, username: str, role: str = 'user'):
    """
    세션에 사용자 정보 저장
    
    Args:
        request: FastAPI Request 객체
        user_id: 사용자 ID
        username: 사용자명
        role: 사용자 역할
    """
    request.session['user_id'] = user_id
    request.session['username'] = username
    request.session['role'] = role


def clear_session(request: Request):
    """
    세션 초기화 (로그아웃)
    
    Args:
        request: FastAPI Request 객체
    """
    request.session.clear()


def is_authenticated(request: Request) -> bool:
    """
    로그인 상태 확인
    
    Args:
        request: FastAPI Request 객체
    
    Returns:
        로그인 여부
    """
    return get_current_user(request) is not None

