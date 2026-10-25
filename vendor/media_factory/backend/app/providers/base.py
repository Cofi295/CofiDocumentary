from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
import re
from typing import Any


class ProviderError(RuntimeError):
    """Base error surfaced to queue jobs without leaking provider internals."""


class ProviderAuthError(ProviderError):
    """Provider credential is missing or rejected."""


class ProviderQuotaError(ProviderError):
    """Provider quota or rate limit is exhausted."""


class ProviderTransientError(ProviderError):
    """Temporary provider failure that can safely be retried."""


def is_retryable_provider_error(exc: Exception) -> bool:
    """Return True only for failures that are reasonably likely to recover."""
    if isinstance(exc, ProviderAuthError):
        return False
    if isinstance(exc, (FileNotFoundError, ValueError, TypeError)):
        return False
    if isinstance(exc, (ProviderQuotaError, ProviderTransientError, TimeoutError, ConnectionError)):
        return True
    message = str(exc).lower()
    session_crash_markers = (
        'live browser session closed',
        'live browser session is unavailable',
        'live browser command waited too long',
        'live browser session did not respond',
        'target crashed',
        'page crashed',
        'target page, context or browser has been closed',
        'context or browser has been closed',
        'browser has been closed',
        'target closed',
    )
    if any(marker in message for marker in session_crash_markers):
        return True
    if not isinstance(exc, ProviderError):
        return False

    if re.search(r'http\s+(?:408|425|429|5\d\d)\b', message):
        return True
    transient_markers = (
        'timed out',
        'timeout',
        'temporarily unavailable',
        'temporary failure',
        'network error',
        'connection reset',
        'connection aborted',
        'connection refused',
        'getaddrinfo',
        'enotfound',
        'dns lookup',
        'name resolution',
        'server unavailable',
        'service unavailable',
        'rate limit',
        'quota exhausted',
    )
    return any(marker in message for marker in transient_markers)


class MediaProvider(ABC):
    async def acquire_job_slot(self, scene: dict[str, Any]) -> Any:
        return None

    async def release_job_slot(self, scene: dict[str, Any], slot: Any) -> None:
        return None

    @abstractmethod
    async def generate(self, scene: dict[str, Any]) -> str:
        raise NotImplementedError


def scene_output_directory(scene: dict[str, Any], fallback: str | Path) -> Path:
    directory = Path(scene.get('_output_directory') or fallback).expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def scene_output_stem(scene: dict[str, Any]) -> str:
    explicit = str(scene.get('_output_stem') or '').strip()
    if explicit:
        return explicit
    sid = scene.get('id')
    if sid:
        return str(sid)
    import uuid
    return f"gen_{uuid.uuid4().hex[:12]}"


def prompt_slug(prompt: str, *, max_length: int = 72) -> str:
    slug = re.sub(r'[^\w]+', '_', prompt.strip(), flags=re.UNICODE).strip('_')
    slug = re.sub(r'_+', '_', slug)
    return (slug[:max_length].rstrip('_') or 'prompt')
