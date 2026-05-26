from __future__ import annotations

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    retry_if_exception_type,
    stop_after_attempt,
    stop_after_delay,
    wait_exponential,
)

from backend.config import settings

_TRANSIENT_EXC: tuple[type[BaseException], ...] = (
    httpx.ConnectError,
    httpx.ReadTimeout,
    httpx.RemoteProtocolError,
)


def _is_5xx(exc: BaseException) -> bool:
    return (
        isinstance(exc, httpx.HTTPStatusError)
        and 500 <= exc.response.status_code < 600
    )


_retry_transient = retry(
    retry=retry_if_exception_type(_TRANSIENT_EXC) | retry_if_exception(_is_5xx),
    stop=stop_after_attempt(3) | stop_after_delay(10),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    reraise=True,
)


async def ping_ollama(timeout: float = 2.0) -> bool:  # noqa: ASYNC109
    """One-shot health probe — no retries, never raises."""
    try:
        async with httpx.AsyncClient(base_url=settings.ollama_host, timeout=timeout) as client:
            resp = await client.get("/api/tags")
            resp.raise_for_status()
        return True
    except Exception:
        return False


@_retry_transient
async def ollama_get(path: str, timeout: float = 30.0) -> httpx.Response:  # noqa: ASYNC109
    """GET against Ollama with bounded retries on transient failures only."""
    async with httpx.AsyncClient(base_url=settings.ollama_host, timeout=timeout) as client:
        resp = await client.get(path)
        resp.raise_for_status()
        return resp


@_retry_transient
async def ollama_generate(
    prompt: str,
    *,
    model: str,
    temperature: float = 0.3,
    max_tokens: int = 200,
    timeout: float = 30.0,  # noqa: ASYNC109  (httpx handles timeout natively)
) -> str:
    """Non-streaming /api/generate completion. Returns the response text.

    Low temperature + a small num_predict keep sections factual and bounded
    (cost-aware). Bounded retries on transient failures; raises otherwise.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature, "num_predict": max_tokens},
    }
    async with httpx.AsyncClient(base_url=settings.ollama_host, timeout=timeout) as client:
        resp = await client.post("/api/generate", json=payload)
        resp.raise_for_status()
        return str(resp.json().get("response", "")).strip()
