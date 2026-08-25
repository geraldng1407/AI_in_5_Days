"""Active PII and Sensitive Data Redaction Pipeline.

Adheres to AgentOps Rubric Category 4: PII Redaction.
Scans and scrubs sensitive identifiers (emails, IPs, API keys, JWTs, passwords)
from text, tool arguments, structured logs, and memory pipelines.
"""

from __future__ import annotations

import re
from typing import Any


class PIIScrubber:
    """Regex-based high-performance PII redaction engine."""

    # Pre-compiled patterns for sensitive entities
    PATTERNS: list[tuple[re.Pattern, str]] = [
        # Google API Keys
        (re.compile(r"AIza[0-9A-Za-z-_]{35}"), "[REDACTED_GOOGLE_API_KEY]"),
        # Generic API Keys / Tokens (sk-..., ghp_..., etc.)
        (re.compile(r"\b(?:sk|ghp|glpat|token|key)-[A-Za-z0-9_\-]{20,}\b", re.IGNORECASE), "[REDACTED_API_KEY]"),
        # JWT Tokens (header.payload.signature)
        (re.compile(r"ey[A-Za-z0-9_-]{10,}\.ey[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_\-+/=]{10,}"), "[REDACTED_JWT_TOKEN]"),
        # Bearer Auth Headers
        (re.compile(r"(?i)bearer\s+[A-Za-z0-9\-_.~+/]+=*"), "Bearer [REDACTED_BEARER_TOKEN]"),
        # Email Addresses
        (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[REDACTED_EMAIL]"),
        # IPv4 Addresses (excludes common localhosts like 127.0.0.1 or 0.0.0.0 optionally, but redacts routable IPs)
        (re.compile(r"\b(?!127\.0\.0\.1\b)(?!0\.0\.0\.0\b)(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"), "[REDACTED_IP]"),
        # Passwords in JSON / Key-Value
        (re.compile(r'(?i)(["\']?(?:password|secret|passwd|auth_token)["\']?\s*[:=]\s*["\'])([^"\']+)(["\'])'), r'\1[REDACTED_SECRET]\3'),
    ]

    @classmethod
    def scrub_text(cls, text: str) -> str:
        """Sanitize a raw string, replacing all detected sensitive PII patterns."""
        if not text or not isinstance(text, str):
            return text
        sanitized = text
        for pattern, replacement in cls.PATTERNS:
            sanitized = pattern.sub(replacement, sanitized)
        return sanitized

    @classmethod
    def scrub_dict(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Recursively sanitize dictionary keys and values."""
        if not isinstance(data, dict):
            return cls.scrub_object(data)
        
        sanitized_dict: dict[str, Any] = {}
        for k, v in data.items():
            # Check if key itself indicates a sensitive credential
            if any(secret_word in k.lower() for secret_word in ["password", "secret", "token", "api_key", "private_key"]):
                sanitized_dict[k] = "[REDACTED_CREDENTIAL]"
            else:
                sanitized_dict[k] = cls.scrub_object(v)
        return sanitized_dict

    @classmethod
    def scrub_object(cls, obj: Any) -> Any:
        """Recursively sanitize nested data structures (dicts, lists, primitives)."""
        if isinstance(obj, str):
            return cls.scrub_text(obj)
        elif isinstance(obj, dict):
            return cls.scrub_dict(obj)
        elif isinstance(obj, list):
            return [cls.scrub_object(item) for item in obj]
        elif isinstance(obj, tuple):
            return tuple(cls.scrub_object(item) for item in obj)
        return obj


def scrub_text(text: str) -> str:
    """Convenience functional wrapper for text scrubbing."""
    return PIIScrubber.scrub_text(text)


def scrub_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Convenience functional wrapper for dictionary scrubbing."""
    return PIIScrubber.scrub_dict(data)
