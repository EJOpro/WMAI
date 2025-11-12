"""
개인정보 마스킹/익명화 유틸리티
벡터DB에 저장하기 전 개인정보를 마스킹하여 프라이버시를 보호합니다.
"""

import re
from typing import Dict, Any, List


def mask_pii(text: str) -> str:
    """
    텍스트에서 개인정보를 마스킹합니다.
    
    Args:
        text (str): 마스킹할 텍스트
        
    Returns:
        str: 마스킹된 텍스트
        
    마스킹 대상:
        - 이메일 주소: user@example.com -> user***@***.com
        - 전화번호: 010-1234-5678 -> 010-****-****
        - 주민등록번호 패턴: 123456-1****** -> 123456-******
        - 신용카드 번호 패턴: 1234-5678-9012-3456 -> 1234-****-****-3456
    """
    if not text:
        return text
    
    # 이메일 주소 마스킹
    text = re.sub(
        r'([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        lambda m: f"{m.group(1)[:3]}***@{'***'}.{m.group(2).split('.')[-1]}",
        text
    )
    
    # 전화번호 마스킹 (010-1234-5678 형식)
    text = re.sub(
        r'(\d{2,3})-(\d{3,4})-(\d{4})',
        lambda m: f"{m.group(1)}-****-****",
        text
    )
    
    # 주민등록번호 패턴 마스킹 (123456-1****** 형식)
    text = re.sub(
        r'(\d{6})-(\d{1})\d{6}',
        lambda m: f"{m.group(1)}-{m.group(2)}******",
        text
    )
    
    # 신용카드 번호 패턴 마스킹 (1234-5678-9012-3456 형식)
    text = re.sub(
        r'(\d{4})-(\d{4})-(\d{4})-(\d{4})',
        lambda m: f"{m.group(1)}-****-****-{m.group(4)}",
        text
    )
    
    return text


def anonymize_user_id(user_id: str) -> str:
    """
    사용자 ID를 익명화합니다 (해시 기반).
    
    Args:
        user_id (str): 원본 사용자 ID
        
    Returns:
        str: 익명화된 사용자 ID (해시 기반)
    """
    import hashlib
    
    if not user_id:
        return "anonymous"
    
    # SHA-256 해시로 익명화 (앞 8자리만 사용)
    hash_obj = hashlib.sha256(user_id.encode('utf-8'))
    anonymized = hash_obj.hexdigest()[:8]
    
    return f"user_{anonymized}"


def sanitize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    메타데이터에서 개인정보를 마스킹/익명화합니다.
    
    Args:
        metadata (Dict[str, Any]): 원본 메타데이터
        
    Returns:
        Dict[str, Any]: 개인정보가 마스킹된 메타데이터
    """
    sanitized = metadata.copy()
    
    # sentence 필드 마스킹
    if 'sentence' in sanitized:
        sanitized['sentence'] = mask_pii(str(sanitized['sentence']))
    
    # user_id 익명화
    if 'user_id' in sanitized:
        sanitized['user_id'] = anonymize_user_id(str(sanitized['user_id']))
    
    # post_id는 해시 기반이므로 그대로 유지 (필요시 추가 마스킹 가능)
    
    return sanitized


def should_mask_field(field_name: str) -> bool:
    """
    특정 필드가 마스킹 대상인지 확인합니다.
    
    Args:
        field_name (str): 필드 이름
        
    Returns:
        bool: 마스킹 대상 여부
    """
    sensitive_fields = {
        'sentence', 'text', 'content', 'message',
        'user_id', 'email', 'phone', 'address'
    }
    
    return field_name.lower() in sensitive_fields

