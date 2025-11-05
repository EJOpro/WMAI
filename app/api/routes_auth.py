"""
인증 API 라우터
회원가입, 로그인, 로그아웃 등 인증 관련 엔드포인트
"""
from fastapi import APIRouter, Request, HTTPException, status, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from app.auth import hash_password, verify_password, set_session_user, clear_session, get_current_user
from app.database import execute_query
import pymysql

router = APIRouter(tags=["auth"])


class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/auth/register")
async def register(request: Request, data: RegisterRequest):
    """
    회원가입
    
    Args:
        username: 사용자명 (3-20자)
        password: 비밀번호 (6자 이상)
    
    Returns:
        성공 메시지 및 사용자 정보
    """
    # 입력 검증
    if not data.username or len(data.username) < 3 or len(data.username) > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="사용자명은 3-20자 사이여야 합니다"
        )
    
    if not data.password or len(data.password) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="비밀번호는 3자 이상이어야 합니다"
        )
    
    # 사용자명 중복 확인
    existing_user = execute_query(
        "SELECT id FROM users WHERE username = %s",
        (data.username,),
        fetch_one=True
    )
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 사용 중인 사용자명입니다"
        )
    
    # 비밀번호 해싱
    hashed_pw = hash_password(data.password)
    
    # 사용자 생성
    try:
        user_id = execute_query(
            "INSERT INTO users (username, password, role, status) VALUES (%s, %s, %s, %s)",
            (data.username, hashed_pw, 'user', 'normal')
        )
        
        # 자동 로그인
        set_session_user(request, user_id, data.username, 'user')
        
        return {
            "success": True,
            "message": "회원가입이 완료되었습니다",
            "user": {
                "id": user_id,
                "username": data.username,
                "role": "user"
            }
        }
    except pymysql.Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"회원가입 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/auth/login")
async def login(request: Request, data: LoginRequest):
    """
    로그인
    
    Args:
        username: 사용자명
        password: 비밀번호
    
    Returns:
        성공 메시지 및 사용자 정보
    """
    # 사용자 조회
    user = execute_query(
        "SELECT id, username, password, role, status FROM users WHERE username = %s",
        (data.username,),
        fetch_one=True
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="사용자명 또는 비밀번호가 올바르지 않습니다"
        )
    
    # 계정 상태 확인
    if user['status'] == 'suspended':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="정지된 계정입니다. 관리자에게 문의하세요"
        )
    
    if user['status'] == 'inactive':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 계정입니다"
        )
    
    # 비밀번호 검증
    if not verify_password(data.password, user['password']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="사용자명 또는 비밀번호가 올바르지 않습니다"
        )
    
    # 세션에 사용자 정보 저장
    set_session_user(request, user['id'], user['username'], user['role'])
    
    return {
        "success": True,
        "message": "로그인되었습니다",
        "user": {
            "id": user['id'],
            "username": user['username'],
            "role": user['role']
        }
    }


@router.post("/auth/logout")
async def logout(request: Request):
    """
    로그아웃
    
    Returns:
        성공 메시지
    """
    clear_session(request)
    
    return {
        "success": True,
        "message": "로그아웃되었습니다"
    }


@router.get("/auth/me")
async def get_me(request: Request):
    """
    현재 로그인한 사용자 정보 조회
    
    Returns:
        사용자 정보 또는 null
    """
    user = get_current_user(request)
    
    if not user:
        return {
            "authenticated": False,
            "user": None
        }
    
    # DB에서 최신 사용자 정보 가져오기
    db_user = execute_query(
        "SELECT id, username, role, status, created_at FROM users WHERE id = %s",
        (user['user_id'],),
        fetch_one=True
    )
    
    if not db_user:
        # 사용자가 삭제된 경우 세션 초기화
        clear_session(request)
        return {
            "authenticated": False,
            "user": None
        }
    
    return {
        "authenticated": True,
        "user": {
            "id": db_user['id'],
            "username": db_user['username'],
            "role": db_user['role'],
            "status": db_user['status'],
            "created_at": db_user['created_at'].isoformat() if db_user['created_at'] else None
        }
    }


@router.post("/auth/check-username")
async def check_username(username: str = Form(...)):
    """
    사용자명 중복 확인
    
    Args:
        username: 확인할 사용자명
    
    Returns:
        사용 가능 여부
    """
    existing_user = execute_query(
        "SELECT id FROM users WHERE username = %s",
        (username,),
        fetch_one=True
    )
    
    return {
        "available": existing_user is None,
        "message": "사용 가능한 사용자명입니다" if not existing_user else "이미 사용 중인 사용자명입니다"
    }

