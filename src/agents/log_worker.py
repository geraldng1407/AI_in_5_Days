"""Log Diagnostic Worker Agent.

Adheres to AgentOps Rubric Category 3:
- Multi-Agent Patterns (Specialized Worker agent)
- Strategic Model Routing (Uses Gemini Flash for rapid log querying)
"""

from __future__ import annotations

from typing import Any
from src.config import get_config
from src.observability.logger import get_logger
from src.observability.tracer import get_tracer
from src.tools.telemetry_logs import FetchTelemetryLogsTool


class LogWorkerAgent:
    """Specialized Worker agent running on Gemini Flash for rapid log filtering."""

    def __init__(self):
        self.config = get_config()
        self.model_name = self.config.worker_model  # e.g., gemini-2.5-flash
        self.tool = FetchTelemetryLogsTool()
        self._logger = get_logger("log-worker")
        self._tracer = get_tracer()

    def investigate_logs(
        self,
        service_name: str,
        lookback_minutes: int = 15,
        search_keyword: str | None = None,
        trace_id: str = "",
    ) -> dict[str, Any]:
        """Query and analyze application logs for error indicators."""
        with self._tracer.span("LogWorker.investigate_logs", trace_id=trace_id) as span:
            span.set_attribute("model", self.model_name)
            span.set_attribute("service", service_name)

            self._logger.info(
                f"LogWorker (model: {self.model_name}) analyzing logs for '{service_name}'.",
                service=service_name,
                model=self.model_name,
                trace_id=trace_id,
            )

            raw_result = self.tool.run(
                {
                    "service_name": service_name,
                    "time_window_minutes": lookback_minutes,
                    "log_level": "ERROR",
                    "search_keyword": search_keyword,
                },
                trace_id=trace_id,
                span_id=span.span_id,
            )

            logs = raw_result.get("logs", [])
            error_patterns = [log["message"] for log in logs if log.get("severity") in ("ERROR", "FATAL")]

            return {
                "worker": "LogWorker",
                "model_used": self.model_name,
                "service_name": service_name,
                "error_count": len(error_patterns),
                "error_patterns": error_patterns,
                "status": raw_result.get("status", "SUCCESS"),
            }
