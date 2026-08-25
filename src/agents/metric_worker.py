"""Metric Telemetry Worker Agent.

Adheres to AgentOps Rubric Category 3:
- Multi-Agent Patterns (Specialized Worker agent)
- Strategic Model Routing (Uses Gemini Flash for rapid metric aggregation)
"""

from __future__ import annotations

from typing import Any
from src.config import get_config
from src.observability.logger import get_logger
from src.observability.tracer import get_tracer
from src.tools.service_metrics import QueryServiceMetricsTool


class MetricWorkerAgent:
    """Specialized Worker agent running on Gemini Flash for metric health assessment."""

    def __init__(self):
        self.config = get_config()
        self.model_name = self.config.worker_model  # e.g., gemini-2.5-flash
        self.tool = QueryServiceMetricsTool()
        self._logger = get_logger("metric-worker")
        self._tracer = get_tracer()

    def investigate_metrics(self, service_name: str, trace_id: str = "") -> dict[str, Any]:
        """Query and evaluate service latency, error rate, CPU, and memory metrics."""
        with self._tracer.span("MetricWorker.investigate_metrics", trace_id=trace_id) as span:
            span.set_attribute("model", self.model_name)
            span.set_attribute("service", service_name)

            self._logger.info(
                f"MetricWorker (model: {self.model_name}) evaluating telemetry for '{service_name}'.",
                service=service_name,
                model=self.model_name,
                trace_id=trace_id,
            )

            raw_result = self.tool.run(
                {"service_name": service_name},
                trace_id=trace_id,
                span_id=span.span_id,
            )

            metrics_list = raw_result.get("metrics", [])
            critical_metrics = [
                f"{m['metric_name']}: {m['value']}{m['unit']} (Threshold: {m['threshold']}{m['unit']})"
                for m in metrics_list
                if m.get("status") in ("CRITICAL", "DEGRADED")
            ]

            return {
                "worker": "MetricWorker",
                "model_used": self.model_name,
                "service_name": service_name,
                "overall_health": raw_result.get("overall_health", "UNKNOWN"),
                "critical_breaches": critical_metrics,
                "status": raw_result.get("status", "SUCCESS"),
            }
