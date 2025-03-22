import pytest
from pathlib import Path
from core.cache import LayeredCache, FileSystemCache, RedisCache

def test_layered_cache():
    cache = LayeredCache()
    cache.add_backend(FileSystemCache())
    
    cache.set("test", b"value")
    assert cache.get("test") == b"value"

def test_redis_cache():
    cache = RedisCache()
    cache.set("redis_test", b"data", ttl=timedelta(seconds=10))
    assert cache.get("redis_test") == b"data"

def test_file_cache_cleanup():
    cache = FileSystemCache()
    cache.set("expired", b"old", ttl=timedelta(seconds=-1))
    assert cache.get("expired") is None