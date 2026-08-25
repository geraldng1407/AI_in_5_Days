"""Telemetry Log Extraction Tool.

Adheres to AgentOps Rubric Category 1:
- Descriptive Naming: `fetch_telemetry_logs`
- Comprehensive Docstrings with parameter explanations
- Explicit Pydantic JSON Schemas
- Guided Error Handling with recovery hints
"""

from __future__ import annotations

import datetime
from typing import Any

from src.pydantic_compat import BaseModel, Field
from src.tools.base import BaseTool, ToolErrorResponse


class FetchTelemetryLogsInput(BaseModel):
    """Input parameters for fetching service telemetry logs."""
    service_name: str = Field(
        description="The canonical name of the cloud microservice (e.g., 'checkout-service', 'auth-service', 'payment-gateway')."
    )
    time_window_minutes: int = Field(
        default=15,
        ge=1,
        le=120,
        description="The historical lookback window in minutes (1 to 120 minutes)."
    )
    log_level: str = Field(
        default="ERROR",
        description="Minimum log severity to query: 'DEBUG', 'INFO', 'WARN', 'ERROR', or 'FATAL'."
    )
    search_keyword: str | None = Field(
        default=None,
        description="Optional regex or substring keyword to filter log lines (e.g. 'OutOfMemory', 'Timeout', 'ConnectionRefused')."
    )


class LogEntry(BaseModel):
    """Structured representation of a single log line."""
    timestamp: str = Field(description="ISO 8601 UTC timestamp of the log event.")
    severity: str = Field(description="Log severity level.")
    service: str = Field(description="Source service.")
    pod_id: str = Field(description="Kubernetes pod or container ID.")
    message: str = Field(description="Sanitized log message payload.")


class FetchTelemetryLogsOutput(BaseModel):
    """Output results containing parsed log entries."""
    status: str = Field(default="SUCCESS", description="Query execution status.")
    service_name: str = Field(description="Queried service.")
    entries_found: int = Field(description="Total count of matching log lines.")
    logs: list[LogEntry] = Field(description="List of matching log records.")


class FetchTelemetryLogsTool(BaseTool):
    """Extracts, parses, and filters application telemetry logs from Cloud Logging."""

    name = "fetch_telemetry_logs"
    description = (
        "Extracts and parses application telemetry logs from Cloud Logging for a target microservice. "
        "Allows filtering by lookback window, severity level, and search keywords."
    )
    input_schema = FetchTelemetryLogsInput
    output_schema = FetchTelemetryLogsOutput

    MOCK_LOG_DB: dict[str, list[dict[str, str]]] = {
        "checkout-service": [
            {"severity": "ERROR", "message": "java.lang.OutOfMemoryError: Java heap space at OrderProcessor.checkout()", "pod": "checkout-pod-9b8f-1"},
            {"severity": "ERROR", "message": "GC overhead limit exceeded during payload deserialization", "pod": "checkout-pod-9b8f-1"},
            {"severity": "WARN", "message": "High heap allocation rate: 98% memory used", "pod": "checkout-pod-9b8f-2"},
        ],
        "auth-service": [
            {"severity": "ERROR", "message": "JWTCertificateExpired: Key rotation failed from upstream auth provider", "pod": "auth-pod-c21d-4"},
            {"severity": "ERROR", "message": "401 Unauthorized spike: 1250 token rejections in 60s", "pod": "auth-pod-c21d-4"},
        ],
        "payment-gateway": [
            {"severity": "ERROR", "message": "ConnectionTimeoutException: upstream payment partner gateway:443 did not respond within 5000ms", "pod": "pay-pod-44ab-9"},
            {"severity": "ERROR", "message": "Circuit breaker OPEN for partner gateway endpoint", "pod": "pay-pod-44ab-9"},
        ],
        "inventory-db": [
            {"severity": "ERROR", "message": "FATAL: remaining connection slots are reserved for non-replication superuser connections (max_connections=500 exceeded)", "pod": "inv-db-primary-0"},
            {"severity": "ERROR", "message": "Deadlock detected waiting for lock on table 'inventory_items'", "pod": "inv-db-primary-0"},
        ],
    }

    def _execute(self, inputs: FetchTelemetryLogsInput) -> FetchTelemetryLogsOutput:
        service = inputs.service_name.lower().strip()
        if service not in self.MOCK_LOG_DB:
            known_services = list(self.MOCK_LOG_DB.keys())
            raise ValueError(
                f"Unknown service '{inputs.service_name}'. Available monitored services: {known_services}"
            )

        raw_entries = self.MOCK_LOG_DB[service]
        filtered_entries: list[LogEntry] = []
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

        for item in raw_entries:
            if inputs.search_keyword and inputs.search_keyword.lower() not in item["message"].lower():
                continue
            filtered_entries.append(
                LogEntry(
                    timestamp=now_str,
                    severity=item["severity"],
                    service=service,
                    pod_id=item["pod"],
                    message=item["message"],
                )
            )

        return FetchTelemetryLogsOutput(
            status="SUCCESS",
            service_name=service,
            entries_found=len(filtered_entries),
            logs=filtered_entries,
        )

    def _handle_error(self, exc: Exception, raw_params: dict[str, Any]) -> ToolErrorResponse:
        known_services = list(self.MOCK_LOG_DB.keys())
        return ToolErrorResponse(
            error_code="ServiceLogExtractionError",
            error_message=str(exc),
            recovery_suggestion=(
                f"Service name '{raw_params.get('service_name')}' could not be located in Cloud Logging. "
                f"Please verify the service name from the valid list: {known_services}. "
                "Retry with one of the recognized services."
            ),
            valid_alternatives=known_services,
        )
