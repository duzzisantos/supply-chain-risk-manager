import time
import hashlib
import json
from typing import Any, Optional
from collections import OrderedDict
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.config import settings


class DataBroker:
    """Caching + rate-limited proxy for all external API calls."""

    def __init__(self, cache_ttl: int = 300, max_cache_size: int = 500):
        self._cache: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._cache_ttl = cache_ttl
        self._max_cache_size = max_cache_size
        self._request_timestamps: list[float] = []

    def _cache_key(self, url: str, params: dict) -> str:
        raw = f"{url}:{json.dumps(params, sort_keys=True)}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def _get_cached(self, key: str) -> Optional[Any]:
        if key in self._cache:
            ts, data = self._cache[key]
            if time.time() - ts < self._cache_ttl:
                self._cache.move_to_end(key)
                return data
            del self._cache[key]
        return None

    def _set_cached(self, key: str, data: Any):
        if len(self._cache) >= self._max_cache_size:
            self._cache.popitem(last=False)
        self._cache[key] = (time.time(), data)

    def _check_rate_limit(self):
        now = time.time()
        window_start = now - 60
        self._request_timestamps = [t for t in self._request_timestamps if t > window_start]
        if len(self._request_timestamps) >= settings.rate_limit_per_minute:
            raise RuntimeError("Rate limit exceeded — try again shortly")
        self._request_timestamps.append(now)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def fetch(self, url: str, params: dict = None, headers: dict = None) -> dict:
        params = params or {}
        cache_key = self._cache_key(url, params)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        self._check_rate_limit()

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params, headers=headers or {})
            response.raise_for_status()
            data = response.json()

        self._set_cached(cache_key, data)
        return data

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def post(self, url: str, payload: dict, headers: dict = None) -> dict:
        self._check_rate_limit()
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload, headers=headers or {})
            response.raise_for_status()
            return response.json()


data_broker = DataBroker()
