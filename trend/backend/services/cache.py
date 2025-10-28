"""Redis 캐시 서비스"""
import redis
import json
import hashlib
from typing import Optional, Any
from config.settings import settings


class CacheService:
    """Redis 캐시 서비스"""
    
    def __init__(self):
        self.client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
        self.default_ttl = settings.CACHE_TTL_SECONDS
    
    def _generate_key(self, prefix: str, **params) -> str:
        """캐시 키 생성"""
        params_str = json.dumps(params, sort_keys=True)
        hash_suffix = hashlib.md5(params_str.encode()).hexdigest()[:8]
        return f"{prefix}:{hash_suffix}"
    
    def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 조회"""
        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            print(f"Cache get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """캐시에 값 저장"""
        try:
            ttl = ttl or self.default_ttl
            serialized = json.dumps(value, default=str)
            self.client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            print(f"Cache set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """캐시에서 값 삭제"""
        try:
            self.client.delete(key)
            return True
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """패턴에 맞는 키들 삭제"""
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            print(f"Cache clear error: {e}")
            return 0
    
    def ping(self) -> bool:
        """Redis 연결 테스트"""
        try:
            return self.client.ping()
        except Exception:
            return False


# 싱글톤 인스턴스
cache_service = CacheService()

