"""
Groq LLM client with built-in rate limiter.
"""

from __future__ import annotations

import time
import threading
from typing import Any

from groq import Groq

import config
from database.crud import track_api_usage


class RateLimiter:
    """Simple sliding-window rate limiter for requests and tokens."""

    def __init__(self):
        self._lock = threading.Lock()
        self._minute_requests: list[float] = []
        self._day_requests: list[float] = []
        self._day_start: float = time.time()
        self._day_count: int = 0

    def can_request(self) -> bool:
        now = time.time()
        with self._lock:
            # Clean minute window
            self._minute_requests = [t for t in self._minute_requests if now - t < 60]
            # Reset day counter if new day
            if now - self._day_start >= 86400:
                self._day_start = now
                self._day_count = 0
            return (
                len(self._minute_requests) < config.RATE_LIMIT_RPM
                and self._day_count < config.RATE_LIMIT_RPD
            )

    def record(self):
        now = time.time()
        with self._lock:
            self._minute_requests.append(now)
            self._day_count += 1

    def wait_if_needed(self):
        """Block until a request slot is available."""
        while not self.can_request():
            time.sleep(1)


# Module-level singleton
_rate_limiter = RateLimiter()
_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=config.GROQ_API_KEY)
    return _client


class GroqClient:
    """Class-based interface for Groq requests, as used by the scheduler."""
    
    def __init__(self):
        self.client = _get_client()

    def chat(self, messages: list[dict[str, str]], preset: str = "coach") -> str:
        return chat(messages, preset=preset)


def chat(
    messages: list[dict[str, str]],
    preset: str = "coach",
    stream: bool = False,
) -> str:
    """
    Send a chat completion request to Groq.

    Args:
        messages: List of {"role": ..., "content": ...} dicts.
        preset: One of "classify", "coach", "summarize".
        stream: If True, return streamed text. For bot use, keep False.

    Returns:
        The assistant's response text.
    """
    _rate_limiter.wait_if_needed()

    params = config.LLM_PRESETS.get(preset, config.LLM_PRESETS["coach"])
    client = _get_client()

    _rate_limiter.record()

    try:
        if stream:
            return _stream_response(client, messages, params)

        completion = client.chat.completions.create(
            model=config.GROQ_MODEL,
            messages=messages,
            temperature=params["temperature"],
            max_completion_tokens=params["max_completion_tokens"],
            reasoning_effort=params.get("reasoning_effort", "medium"),
        )

        response_text = completion.choices[0].message.content or ""

        # Track usage asynchronously (fire-and-forget in sync context)
        _track_usage_sync(completion)

        return response_text

    except Exception as e:
        return f"[LLM Error: {str(e)}]"


def _stream_response(client: Groq, messages: list, params: dict) -> str:
    """Handle streaming and collect full text."""
    chunks = []
    completion = client.chat.completions.create(
        model=config.GROQ_MODEL,
        messages=messages,
        temperature=params["temperature"],
        max_completion_tokens=params["max_completion_tokens"],
        reasoning_effort=params.get("reasoning_effort", "medium"),
        stream=True,
    )
    for chunk in completion:
        text = chunk.choices[0].delta.content or ""
        chunks.append(text)
    return "".join(chunks)


def _track_usage_sync(completion: Any) -> None:
    """Track API usage synchronously."""
    try:
        usage = completion.usage
        if usage:
            track_api_usage(
                request_count=1,
                token_count=usage.total_tokens or 0,
            )
    except Exception:
        pass  # Don't fail the main request for tracking
