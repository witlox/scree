import time
from typing import Generic, TypeVar

V = TypeVar("V")


class TtlCache(Generic[V]):
    """Tiny per-process short-TTL cache (AR-08: resolve readable Spaces ONCE, cached
    with a short TTL — never per-item/per-request upstream calls). Bounded staleness
    equals the TTL. Spike: in-memory; a multi-replica deploy would use shared state."""

    def __init__(self, ttl: float = 60.0) -> None:
        self._ttl = ttl
        self._store: dict[str, tuple[float, V]] = {}

    def get(self, key: str) -> V | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires, value = entry
        if time.monotonic() >= expires:
            self._store.pop(key, None)
            return None
        return value

    def put(self, key: str, value: V) -> None:
        self._store[key] = (time.monotonic() + self._ttl, value)
