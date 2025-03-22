import redis
from datetime import timedelta
from .layered_cache import CacheBackend

class RedisCache(CacheBackend):
    def __init__(self):
        self.client = redis.Redis(
            host='localhost',
            port=6379,
            db=1,  # Отдельная БД для кэша
            decode_responses=False
        )

    def get(self, key: str) -> Optional[bytes]:
        return self.client.get(key)

    def set(self, key: str, value: bytes, ttl: Optional[timedelta] = None):
        self.client.set(
            name=key,
            value=value,
            ex=int(ttl.total_seconds()) if ttl else None
        )