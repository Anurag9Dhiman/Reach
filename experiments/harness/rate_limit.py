"""Retry/pacing helper for real Gemini API calls.

Discovered while running E1/E9 concurrently: the free tier enforces a
*per-minute* rate limit (observed: 15 req/min for gemini-3.1-flash-lite),
not just a daily quota - concurrent experiments (or a tight loop within one
experiment) can trip a 429 well before any daily cap. This wraps a call with
a short retry-with-backoff so a single transient rate-limit or 503 doesn't
crash an entire experiment script, and exposes a plain pacing sleep so
scripts making many sequential real calls stay comfortably under the
per-minute ceiling.
"""
from __future__ import annotations

import time
from typing import Callable, TypeVar

T = TypeVar("T")

MIN_SECONDS_BETWEEN_CALLS = 4.5  # ~13/min, comfortably under the observed 15/min cap


def pace() -> None:
    time.sleep(MIN_SECONDS_BETWEEN_CALLS)


def call_with_retry(fn: Callable[[], T], max_attempts: int = 3, backoff_seconds: float = 15.0) -> T:
    """Retries fn() on any exception (rate limits and transient upstream
    errors surface as exceptions from google-genai) with linear backoff.
    Re-raises the last exception if all attempts fail."""
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - deliberately broad: any transient API error should retry
            last_exc = exc
            if attempt < max_attempts:
                wait = backoff_seconds * attempt
                print(f"    (attempt {attempt}/{max_attempts} failed: {exc!s:.150}; retrying in {wait:.0f}s)")
                time.sleep(wait)
    assert last_exc is not None
    raise last_exc
