"""
cache.py - Simple in-memory TTL (Time-To-Live) cache.

Used by the pricing tool to avoid redundant lookups within a session.
"""

from __future__ import annotations

import time
from typing import Any, Optional


class TTLCache:
    """A lightweight dictionary-backed cache with per-key expiration."""

    def __init__(self, default_ttl: int = 3600) -> None:
        """
        Args:
            default_ttl: Default time-to-live in seconds (default: 1 hour).
        """
        self._store: dict[str, tuple[Any, float]] = {}
        self._default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache if it exists and hasn't expired."""
        if key in self._store:
            value, expiry = self._store[key]
            if time.time() < expiry:
                return value
            # Expired - remove it
            del self._store[key]
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Store a value with optional custom TTL.

        Args:
            key: Cache key.
            value: Value to store.
            ttl: Time-to-live in seconds. Uses default if not specified.
        """
        ttl = ttl if ttl is not None else self._default_ttl
        self._store[key] = (value, time.time() + ttl)

    def clear(self) -> None:
        """Clear all cached entries."""
        self._store.clear()

    def __contains__(self, key: str) -> bool:
        """Check if a non-expired key exists in the cache."""
        return self.get(key) is not None

    def __len__(self) -> int:
        """Return number of non-expired entries."""
        now = time.time()
        return sum(1 for _, (_, exp) in self._store.items() if now < exp)
