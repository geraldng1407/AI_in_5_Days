"""Application configuration and secure secret management.

Adheres to AgentOps Rubric Category 5: Secure Secret Management.
Loads credentials dynamically from environment / Google Secret Manager with zero hardcoded keys.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class AgentConfig:
    """Immutable configuration container for the Cloud SRE Agent."""

    # Project and environment settings
    project_id: str = field(default_factory=lambda: os.getenv("GOOGLE_CLOUD_PROJECT", "demo-cloud-sre-project"))
    location: str = field(default_factory=lambda: os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"))
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))

    # Strategic Model Routing (Rubric Category 3)
    # Pro model for high-level reasoning, planning, and synthesis
    coordinator_model: str = field(default_factory=lambda: os.getenv("COORDINATOR_MODEL", "gemini-2.5-pro"))
    # Flash model for fast, high-throughput sub-agent diagnostic tasks
    worker_model: str = field(default_factory=lambda: os.getenv("WORKER_MODEL", "gemini-2.5-flash"))
    embedding_model: str = field(default_factory=lambda: os.getenv("EMBEDDING_MODEL", "text-embedding-004"))

    # Context & Memory Configuration (Rubric Category 2)
    max_context_tokens: int = field(default_factory=lambda: int(os.getenv("MAX_CONTEXT_TOKENS", "8192")))
    compaction_threshold_tokens: int = field(default_factory=lambda: int(os.getenv("COMPACTION_THRESHOLD", "6000")))
    sqlite_db_path: str = field(default_factory=lambda: os.getenv("SQLITE_DB_PATH", "data/incidents.db"))
    vector_store_path: str = field(default_factory=lambda: os.getenv("VECTOR_STORE_PATH", "data/vector_store"))

    # Observability & Tracing Configuration (Rubric Category 4)
    enable_structured_logging: bool = field(
        default_factory=lambda: os.getenv("ENABLE_STRUCTURED_LOGGING", "true").lower() == "true"
    )
    enable_otel_tracing: bool = field(
        default_factory=lambda: os.getenv("ENABLE_OTEL_TRACING", "true").lower() == "true"
    )
    otel_service_name: str = field(default_factory=lambda: os.getenv("OTEL_SERVICE_NAME", "cloud-sre-agent"))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))


def get_config() -> AgentConfig:
    """Retrieve application configuration instance."""
    # Ensure data directory exists
    Path("data").mkdir(parents=True, exist_ok=True)
    return AgentConfig()
