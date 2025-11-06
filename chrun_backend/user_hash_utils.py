"""
사용자 해시 생성 유틸리티
같은 user_id는 항상 같은 해시값을 반환합니다 (일관성 보장)
"""
import hashlib
import secrets
import os
from typing import Optional

# 환경 변수에서 salt 가져오기 (보안 강화)
# .env 파일에 USER_HASH_SALT=your_secret_salt 추가 권장
USER_HASH_SALT = os.getenv('USER_HASH_SALT', 'wmai_secret_salt_2024')

def generate_user_hash(user_id: Optional[int] = None) -> str:
    """
    사용자 해시 생성
    
    Args:
        user_id: 로그인 사용자의 user_id (있으면 일관된 해시, 없으면 랜덤)
    
    Returns:
        SHA-256 해시값 (64자 hex 문자열)
        
    예시:
        >>> hash1 = generate_user_hash(42)
        >>> hash2 = generate_user_hash(42)
        >>> hash1 == hash2  # True - 항상 같은 값
        
    중요:
        - 같은 user_id는 항상 같은 해시값을 반환합니다
        - 이는 이탈 분석에서 같은 사용자의 이벤트를 추적하기 위해 필수입니다
        - user_id가 None이면 랜덤 해시를 생성합니다 (익명 사용자용)
    """
    if user_id is not None:
        # 로그인 사용자: user_id + salt로 일관된 해시 생성
        # 같은 user_id는 항상 같은 해시값을 가짐 (중요!)
        hash_input = f"{user_id}{USER_HASH_SALT}".encode('utf-8')
        return hashlib.sha256(hash_input).hexdigest()
    else:
        # 비로그인/익명 사용자: 랜덤 해시 생성
        random_bytes = secrets.token_bytes(32)
        return hashlib.sha256(random_bytes).hexdigest()

def get_user_hash_for_event(user_id: Optional[int] = None) -> str:
    """
    이벤트 기록용 user_hash 생성 (간편 함수)
    
    Args:
        user_id: 로그인 사용자의 user_id (None이면 익명 사용자)
    
    Returns:
        SHA-256 해시값
    
    사용 예시:
        # 로그인 사용자
        user_hash = get_user_hash_for_event(user_id=42)
        
        # 익명 사용자
        user_hash = get_user_hash_for_event()
    """
    return generate_user_hash(user_id)

