from pathlib import Path
import hashlib
from .layered_cache import CacheBackend
from datetime import datetime, timedelta

class FileSystemCache(CacheBackend):
    def __init__(self, cache_dir=".cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

    def _get_path(self, key: str) -> Path:
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / key_hash[:2] / key_hash[2:4] / key_hash

    def get(self, key: str) -> Optional[bytes]:
        path = self._get_path(key)
        if not path.exists():
            return None
            
        with open(path, "rb") as f:
            return f.read()

    def set(self, key: str, value: bytes, ttl: Optional[timedelta] = None):
        path = self._get_path(key)
        path.parent.mkdir(exist_ok=True, parents=True)
        
        with open(path, "wb") as f:
            f.write(value)