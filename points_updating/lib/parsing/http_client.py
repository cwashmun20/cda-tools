"""Rate-limited, cacheable HTTP client for results-source scrapers.

Every results-source module (O2CM, Ballroom Comp Express, CompOrganizer)
fetches from a live third-party site not under our control. This is shared
infrastructure proven necessary during evaluation: O2CM's site returned a
blanket 403 across every endpoint after an unthrottled ~135-request burst.
"""

import hashlib
import json
import pickle
import time
from pathlib import Path
from typing import Callable, Optional, Protocol

import requests

_THROTTLE_STATUS_CODES = frozenset({403, 429})


class _RequestTransport(Protocol):
    """The minimal interface ThrottledClient needs from a session -
    `requests.Session` satisfies this already; tests inject a lighter fake.
    """

    def request(self, method: str, url: str, **kwargs) -> requests.Response: ...


class ThrottledClient:
    """HTTP client enforcing a minimum delay between requests, exponential
    backoff-and-retry on throttle responses, and optional on-disk response
    caching.
    """

    def __init__(
        self,
        min_delay_seconds: float = 1.0,
        max_retries: int = 5,
        backoff_base_seconds: float = 2.0,
        session: Optional[_RequestTransport] = None,
        cache_dir: Optional[Path] = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ):
        """Create a ThrottledClient.

        Args:
            min_delay_seconds: Minimum time between the start of one request
                and the start of the next, enforced regardless of how long
                a request (or its retries) took.
            max_retries: How many additional attempts to make after a
                throttle response, before giving up and returning it as-is.
            backoff_base_seconds: Delay before the first retry; doubles on
                each subsequent attempt.
            session: Injectable HTTP transport - defaults to a real
                `requests.Session`; tests supply a fake.
            cache_dir: If set, successful (non-throttled) responses are
                cached to disk here, keyed by request method/URL/params/
                body, so repeated runs against the same data don't re-hit
                the live site. Throttled responses are never cached, so a
                later run retries fresh rather than replaying a stuck
                failure.
            sleep: Injectable sleep function - tests supply a fake so delay/
                backoff tests don't actually wait.
            clock: Injectable monotonic clock - tests supply a fake paired
                with `sleep` so delay tracking is deterministic.
        """
        self.min_delay_seconds = min_delay_seconds
        self.max_retries = max_retries
        self.backoff_base_seconds = backoff_base_seconds
        self._session = session if session is not None else requests.Session()
        self._cache_dir = cache_dir
        self._sleep = sleep
        self._clock = clock
        self._last_request_time: Optional[float] = None

    def get(self, url: str, **kwargs) -> requests.Response:
        return self._request("GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> requests.Response:
        return self._request("POST", url, **kwargs)

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        cache_key = self._cache_key(method, url, kwargs)
        cached = self._read_cache(cache_key)
        if cached is not None:
            return cached

        response = self._request_with_backoff(method, url, **kwargs)
        if response.status_code not in _THROTTLE_STATUS_CODES:
            self._write_cache(cache_key, response)
        return response

    def _request_with_backoff(self, method: str, url: str, **kwargs) -> requests.Response:
        attempt = 0
        while True:
            self._wait_for_min_delay()
            response = self._session.request(method, url, **kwargs)
            if response.status_code not in _THROTTLE_STATUS_CODES or attempt >= self.max_retries:
                return response
            self._sleep(self.backoff_base_seconds * (2**attempt))
            attempt += 1

    def _wait_for_min_delay(self) -> None:
        if self._last_request_time is not None:
            remaining = self.min_delay_seconds - (self._clock() - self._last_request_time)
            if remaining > 0:
                self._sleep(remaining)
        self._last_request_time = self._clock()

    def _cache_key(self, method: str, url: str, kwargs: dict) -> str:
        payload = json.dumps(
            {
                "method": method,
                "url": url,
                "params": kwargs.get("params"),
                "data": kwargs.get("data"),
            },
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _cache_path(self, cache_key: str) -> Optional[Path]:
        if self._cache_dir is None:
            return None
        return self._cache_dir / f"{cache_key}.pickle"

    def _read_cache(self, cache_key: str) -> Optional[requests.Response]:
        path = self._cache_path(cache_key)
        if path is None or not path.is_file():
            return None
        with open(path, "rb") as f:
            return pickle.load(f)

    def _write_cache(self, cache_key: str, response: requests.Response) -> None:
        path = self._cache_path(cache_key)
        if path is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(response, f)
