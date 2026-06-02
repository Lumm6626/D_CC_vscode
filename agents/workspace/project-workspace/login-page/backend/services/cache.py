import time
from typing import Optional, Dict

class SimpleCache:
    """Simple in-memory cache with expiration"""
    def __init__(self):
        self._store: Dict[str, tuple[str, float]] = {}

    def set(self, key: str, value: str, ttl: int = 300):
        """Set value with TTL in seconds"""
        self._store[key] = (value, time.time() + ttl)

    def get(self, key: str) -> Optional[str]:
        """Get value if exists and not expired"""
        if key not in self._store:
            return None
        value, expiry = self._store[key]
        if time.time() > expiry:
            del self._store[key]
            return None
        return value

    def delete(self, key: str):
        """Delete key"""
        self._store.pop(key, None)

    def exists(self, key: str) -> bool:
        """Check if key exists and not expired"""
        return self.get(key) is not None

cache = SimpleCache()