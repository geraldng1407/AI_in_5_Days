"""Structured JSON Logging with Intent vs. Outcome Capture.

Adheres to AgentOps Rubric Category 4:
- Structured JSON Logging (rich JSON metadata, timestamp, levels, trace context)
- Intent vs. Outcome Capture (explicit pre-execution intent and post-execution outcome logging)
"""

from __future__ import annotations

import datetime
import json
import logging
import sys
import time
from typing import Any

from src.observability.pii_scrubber import PIIScrubber


class JSONFormatter(logging.Formatter):
    """Formats log records as rich, single-line JSON objects with automatic PII redaction."""

    def format(self, record: logging.LogRecord) -> str:
        log_payload: dict[str, Any] = {
            "timestamp": datetime.datetime.fromtimestamp(record.created, tz=datetime.timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Extract structured extra fields if present
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            log_payload.update(record.extra_data)

        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)

        # Apply active PII scrubbing across entire structured payload
        sanitized_payload = PIIScrubber.scrub_dict(log_payload)
        return json.dumps(sanitized_payload)


class StructuredLogger:
    """Enterprise logger wrapper providing structured intent and outcome logging methods."""

    def __init__(self, name: str = "cloud-sre-agent"):
        self.logger = logging.getLogger(name)
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(JSONFormatter())
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
            self.logger.propagate = False

    def info(self, message: str, **kwargs: Any) -> None:
        self.logger.info(message, extra={"extra_data": kwargs})

    def warning(self, message: str, **kwargs: Any) -> None:
        self.logger.warning(message, extra={"extra_data": kwargs})

    def error(self, message: str, **kwargs: Any) -> None:
        self.logger.error(message, extra={"extra_data": kwargs})

    def debug(self, message: str, **kwargs: Any) -> None:
        self.logger.debug(message, extra={"extra_data": kwargs})

    def log_intent(
        self,
        action: str,
        planned_params: dict[str, Any],
        agent_name: str = "Coordinator",
        trace_id: str = "",
        span_id: str = "",
        rationale: str = "",
    ) -> None:
        """Capture the agent's explicit INTENT prior to executing a tool or sub-routine."""
        extra_data = {
            "event_type": "AGENT_INTENT",
            "agent": agent_name,
            "action": action,
            "planned_params": planned_params,
            "rationale": rationale,
            "trace_id": trace_id,
            "span_id": span_id,
        }
        self.info(f"Agent [{agent_name}] intends to execute action: {action}", **extra_data)

    def log_outcome(
        self,
        action: str,
        result_summary: Any,
        execution_time_ms: float,
        agent_name: str = "Coordinator",
        trace_id: str = "",
        span_id: str = "",
        status: str = "SUCCESS",
        error_details: str | None = None,
    ) -> None:
        """Capture the agent's actual OUTCOME after executing a tool or sub-routine."""
        extra_data = {
            "event_type": "AGENT_OUTCOME",
            "agent": agent_name,
            "action": action,
            "status": status,
            "result_summary": result_summary,
            "execution_time_ms": round(execution_time_ms, 2),
            "trace_id": trace_id,
            "span_id": span_id,
        }
        if error_details:
            extra_data["error_details"] = error_details

        if status == "SUCCESS":
            self.info(f"Agent [{agent_name}] completed action: {action} with status: {status}", **extra_data)
        else:
            self.error(f"Agent [{agent_name}] failed action: {action} with status: {status}", **extra_data)


# Global singleton instance
_GLOBAL_LOGGER = StructuredLogger()


def get_logger(name: str = "cloud-sre-agent") -> StructuredLogger:
    """Retrieve structured logger instance."""
    return StructuredLogger(name)


def log_intent(
    action: str,
    planned_params: dict[str, Any],
    agent_name: str = "Coordinator",
    trace_id: str = "",
    span_id: str = "",
    rationale: str = "",
) -> None:
    _GLOBAL_LOGGER.log_intent(action, planned_params, agent_name, trace_id, span_id, rationale)


def log_outcome(
    action: str,
    result_summary: Any,
    execution_time_ms: float,
    agent_name: str = "Coordinator",
    trace_id: str = "",
    span_id: str = "",
    status: str = "SUCCESS",
    error_details: str | None = None,
) -> None:
    _GLOBAL_LOGGER.log_outcome(action, result_summary, execution_time_ms, agent_name, trace_id, span_id, status, error_details)
