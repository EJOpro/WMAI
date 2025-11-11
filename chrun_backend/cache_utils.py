"""
캐시 키 생성 및 관리 유틸리티
모든 분석 입력을 반영한 캐시 키 생성 및 구조화된 로그 관리
"""
import hashlib
import json
from typing import Dict, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text


def calculate_dataset_hash(db: Session) -> str:
    """데이터셋 해시 계산 (데이터 변경 감지용)
    
    데이터베이스의 이벤트 수, 최신 날짜, 고유 사용자 수를 기반으로 해시 생성
    민감정보는 포함하지 않음 (통계 정보만 사용)
    
    Args:
        db: 데이터베이스 세션
    
    Returns:
        SHA-256 해시값 (64자 hex 문자열)
    """
    try:
        # 데이터셋 통계 정보 수집 (민감정보 제외)
        from .chrun_models import Event
        
        # 총 이벤트 수
        total_events = db.query(Event).count()
        
        # 고유 사용자 수
        unique_users = db.query(Event.user_hash).distinct().count()
        
        # 최신 이벤트 날짜
        latest_event = db.query(Event.created_at).order_by(Event.created_at.desc()).first()
        latest_date = latest_event.created_at.isoformat() if latest_event else None
        
        # 가장 오래된 이벤트 날짜
        oldest_event = db.query(Event.created_at).order_by(Event.created_at.asc()).first()
        oldest_date = oldest_event.created_at.isoformat() if oldest_event else None
        
        # 해시 생성용 데이터 (민감정보 제외)
        dataset_signature = {
            "total_events": total_events,
            "unique_users": unique_users,
            "latest_date": latest_date,
            "oldest_date": oldest_date
        }
        
        # JSON 직렬화 후 해시 생성
        dataset_json = json.dumps(dataset_signature, sort_keys=True)
        dataset_hash = hashlib.sha256(dataset_json.encode('utf-8')).hexdigest()
        
        return dataset_hash
        
    except Exception as e:
        # 오류 발생 시 기본 해시 반환 (캐시 미스 유도)
        print(f"[WARNING] 데이터셋 해시 계산 실패: {e}")
        return hashlib.sha256(b"error").hexdigest()


def generate_cache_key(
    dataset_hash: str,
    start_month: str,
    end_month: str,
    segments: Dict,
    threshold: int,
    model: str = "gpt-4o-mini",
    prompt_v: str = "v1"
) -> str:
    """분석 캐시 키 생성
    
    모든 분석 입력을 반영한 캐시 키 생성:
    - dataset_hash: 데이터셋 변경 감지
    - start_end: 분석 기간
    - segments_sorted: 세그먼트 설정 (정렬된 형태)
    - threshold: 임계값
    - model: LLM 모델명
    - prompt_v: 프롬프트 버전
    
    Args:
        dataset_hash: 데이터셋 해시값
        start_month: 시작 월 (YYYY-MM)
        end_month: 종료 월 (YYYY-MM)
        segments: 세그먼트 설정 딕셔너리
        threshold: 최소 이벤트 수
        model: LLM 모델명 (기본값: "gpt-4o-mini")
        prompt_v: 프롬프트 버전 (기본값: "v1")
    
    Returns:
        캐시 키 문자열
    """
    # 세그먼트 설정 정렬 (일관성 보장)
    segments_sorted = "_".join([
        f"{k}:{v}" 
        for k, v in sorted(segments.items())
    ])
    
    # start_end 형식
    start_end = f"{start_month}:{end_month}"
    
    # 캐시 키 구성
    cache_key = f"churn_analysis:{dataset_hash}:{start_end}:{segments_sorted}:{threshold}:{model}:{prompt_v}"
    
    return cache_key


def log_cache_event(
    event_type: str,  # "hit", "miss", "invalidate"
    cache_key: str,
    dataset_hash: Optional[str] = None,
    additional_info: Optional[Dict] = None
) -> None:
    """캐시 이벤트 구조화 로그 출력
    
    Args:
        event_type: 이벤트 타입 ("hit", "miss", "invalidate")
        cache_key: 캐시 키
        dataset_hash: 데이터셋 해시 (선택적)
        additional_info: 추가 정보 (선택적)
    """
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
        "cache_key": cache_key,
        "dataset_hash": dataset_hash,
        **(additional_info or {})
    }
    
    # JSON 형식으로 로그 출력
    print(f"[CACHE_EVENT] {json.dumps(log_entry, ensure_ascii=False)}")


def log_cache_hit(cache_key: str, dataset_hash: Optional[str] = None) -> None:
    """캐시 히트 로그"""
    log_cache_event("hit", cache_key, dataset_hash)


def log_cache_miss(cache_key: str, dataset_hash: Optional[str] = None, reason: Optional[str] = None) -> None:
    """캐시 미스 로그"""
    additional_info = {"reason": reason} if reason else None
    log_cache_event("miss", cache_key, dataset_hash, additional_info)


def log_cache_invalidate(
    cache_key: Optional[str] = None,
    pattern: Optional[str] = None,
    deleted_count: Optional[int] = None,
    reason: Optional[str] = None
) -> None:
    """캐시 무효화 로그"""
    additional_info = {}
    if pattern:
        additional_info["pattern"] = pattern
    if deleted_count is not None:
        additional_info["deleted_count"] = deleted_count
    if reason:
        additional_info["reason"] = reason
    
    log_cache_event("invalidate", cache_key or "pattern_based", None, additional_info)

