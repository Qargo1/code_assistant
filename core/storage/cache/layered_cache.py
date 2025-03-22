from typing import Optional
import logging
from datetime import timedelta

class LayeredCache:
    def __init__(self):
        self.backends = []
        self.logger = logging.getLogger(__name__)

    def add_backend(self, backend):
        self.backends.append(backend)

    def get(self, key: str) -> Optional[bytes]:
        """Чтение с приоритетом быстрых бэкендов"""
        for backend in self.backends:
            if value := backend.get(key):
                self.logger.debug(f"Cache hit in {backend.__class__.__name__} for {key}")
                return value
        return None

    def set(self, key: str, value: bytes, ttl: Optional[timedelta] = None):
        """Запись во все бэкенды"""
        for backend in self.backends:
            try:
                backend.set(key, value, ttl)
            except Exception as e:
                self.logger.error(f"Error writing to {backend.__class__.__name__}: {str(e)}")

class CacheBackend:
    def get(self, key: str) -> Optional[bytes]:
        raise NotImplementedError

    def set(self, key: str, value: bytes, ttl: Optional[timedelta] = None):
        raise NotImplementedError