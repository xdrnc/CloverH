"""Simple in-memory cache with TTL and prefix invalidation."""
import threading
import time
from typing import Optional, Any, Dict


class SimpleCache:
    def __init__(self, ttl: int = 60):
        self._cache: Dict[str, tuple[Any, float]] = {}
        self._ttl = ttl
        self._lock = threading.RLock()
        self._stats = {"hits": 0, "misses": 0}
    
    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._cache:
                value, timestamp = self._cache[key]
                if time.time() - timestamp < self._ttl:
                    self._stats["hits"] += 1
                    return value
                del self._cache[key]
            self._stats["misses"] += 1
            return None
    
    def set(self, key: str, value: Any):
        with self._lock:
            self._cache[key] = (value, time.time())
    
    def invalidate_prefix(self, prefix: str):
        with self._lock:
            keys_to_delete = [k for k in self._cache if k.startswith(prefix)]
            for k in keys_to_delete:
                del self._cache[k]
    
    def invalidate_all(self):
        with self._lock:
            self._cache.clear()
    
    def stats(self) -> Dict[str, int]:
        with self._lock:
            return self._stats.copy()


# Global instance
cache = SimpleCache(ttl=60)


def events_cache_key(mrn: str) -> str:
    return f"events:{mrn}"


def invalidate_events_cache():
    """Call after any patient or event write operation."""
    cache.invalidate_prefix("events:")