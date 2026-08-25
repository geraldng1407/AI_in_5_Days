"""Service Metrics Query Tool.

Adheres to AgentOps Rubric Category 1:
- Descriptive Naming: `query_service_metrics`
- Comprehensive Docstrings with parameter explanations
- Explicit Pydantic JSON Schemas
- Guided Error Handling with recovery hints
"""

from __future__ import annotations

from typing import Any
from src.pydantic_compat import BaseModel, Field
from src.tools.base import BaseTool, ToolErrorResponse


class QueryServiceMetricsInput(BaseModel):
    """Input parameters for querying cloud service operational metrics."""
    service_name: str = Field(
        description="The canonical name of the cloud service (e.g., 'checkout-service', 'auth-service', 'inventory-db')."
    )
    metric_names: list[str] = Field(
        default_factory=lambda: ["latency_p95_ms", "latency_p99_ms", "error_rate_pct", "cpu_utilization_pct", "memory_utilization_pct"],
        description="List of metrics to retrieve. Supported: 'latency_p95_ms', 'latency_p99_ms', 'error_rate_pct', 'cpu_utilization_pct', 'memory_utilization_pct', 'active_connections'."
    )
    time_window_minutes: int = Field(
        default=15,
        ge=1,
        le=120,
        description="Lookback window in minutes."
    )


class MetricDataPoint(BaseModel):
    """Represents a single metric value and health indicator."""
    metric_name: str = Field(description="Identifier of the metric.")
    value: float = Field(description="Numerical value of the metric.")
    unit: str = Field(description="Measurement unit (e.g., 'ms', '%', 'count').")
    threshold: float = Field(description="Configured SLO/alert threshold.")
    status: str = Field(description="'NORMAL', 'DEGRADED', or 'CRITICAL'.")


class QueryServiceMetricsOutput(BaseModel):
    """Output result containing aggregated service metrics."""
    status: str = Field(default="SUCCESS", description="Execution status.")
    service_name: str = Field(description="Target service.")
    overall_health: str = Field(description="'HEALTHY', 'DEGRADED', or 'CRITICAL'.")
    metrics: list[MetricDataPoint] = Field(description="List of retrieved metric data points.")


class QueryServiceMetricsTool(BaseTool):
    """Queries latency, error rates, CPU, and memory telemetry from Cloud Monitoring."""

    name = "query_service_metrics"
    description = (
        "Queries Cloud Monitoring for performance telemetry including P95/P99 latency, "
        "HTTP error rates, CPU usage, and memory saturation for a specified service."
    )
    input_schema = QueryServiceMetricsInput
    output_schema = QueryServiceMetricsOutput

    SUPPORTED_METRICS = {
        "latency_p95_ms", "latency_p99_ms", "error_rate_pct",
        "cpu_utilization_pct", "memory_utilization_pct", "active_connections"
    }

    MOCK_METRICS_DB: dict[str, dict[str, tuple[float, str, float, str]]] = {
        "checkout-service": {
            "latency_p95_ms": (4500.0, "ms", 500.0, "CRITICAL"),
            "latency_p99_ms": (8200.0, "ms", 1000.0, "CRITICAL"),
            "error_rate_pct": (24.5, "%", 1.0, "CRITICAL"),
            "cpu_utilization_pct": (45.0, "%", 80.0, "NORMAL"),
            "memory_utilization_pct": (98.5, "%", 85.0, "CRITICAL"),
            "active_connections": (320.0, "count", 1000.0, "NORMAL"),
        },
        "auth-service": {
            "latency_p95_ms": (120.0, "ms", 200.0, "NORMAL"),
            "latency_p99_ms": (250.0, "ms", 400.0, "NORMAL"),
            "error_rate_pct": (52.0, "%", 0.5, "CRITICAL"),
            "cpu_utilization_pct": (30.0, "%", 75.0, "NORMAL"),
            "memory_utilization_pct": (42.0, "%", 80.0, "NORMAL"),
            "active_connections": (150.0, "count", 500.0, "NORMAL"),
        },
        "inventory-db": {
            "latency_p95_ms": (1800.0, "ms", 100.0, "CRITICAL"),
            "latency_p99_ms": (4200.0, "ms", 250.0, "CRITICAL"),
            "error_rate_pct": (18.2, "%", 0.1, "CRITICAL"),
            "cpu_utilization_pct": (96.0, "%", 80.0, "CRITICAL"),
            "memory_utilization_pct": (88.0, "%", 85.0, "DEGRADED"),
            "active_connections": (500.0, "count", 500.0, "CRITICAL"),
        },
        "payment-gateway": {
            "latency_p95_ms": (5200.0, "ms", 800.0, "CRITICAL"),
            "latency_p99_ms": (9800.0, "ms", 1500.0, "CRITICAL"),
            "error_rate_pct": (35.0, "%", 1.0, "CRITICAL"),
            "cpu_utilization_pct": (25.0, "%", 75.0, "NORMAL"),
            "memory_utilization_pct": (38.0, "%", 80.0, "NORMAL"),
            "active_connections": (80.0, "count", 400.0, "NORMAL"),
        }
    }

    def _execute(self, inputs: QueryServiceMetricsInput) -> QueryServiceMetricsOutput:
        service = inputs.service_name.lower().strip()
        if service not in self.MOCK_METRICS_DB:
            known_services = list(self.MOCK_METRICS_DB.keys())
            raise ValueError(f"Service '{inputs.service_name}' not found. Known services: {known_services}")

        invalid_metrics = [m for m in inputs.metric_names if m not in self.SUPPORTED_METRICS]
        if invalid_metrics:
            raise ValueError(
                f"Unsupported metric names requested: {invalid_metrics}. Supported metrics: {list(self.SUPPORTED_METRICS)}"
            )

        svc_metrics = self.MOCK_METRICS_DB[service]
        datapoints: list[MetricDataPoint] = []
        is_critical = False
        is_degraded = False

        for metric in inputs.metric_names:
            if metric in svc_metrics:
                val, unit, thresh, status = svc_metrics[metric]
                if status == "CRITICAL":
                    is_critical = True
                elif status == "DEGRADED":
                    is_degraded = True
                datapoints.append(
                    MetricDataPoint(
                        metric_name=metric,
                        value=val,
                        unit=unit,
                        threshold=thresh,
                        status=status,
                    )
                )

        overall = "CRITICAL" if is_critical else ("DEGRADED" if is_degraded else "HEALTHY")

        return QueryServiceMetricsOutput(
            status="SUCCESS",
            service_name=service,
            overall_health=overall,
            metrics=datapoints,
        )

    def _handle_error(self, exc: Exception, raw_params: dict[str, Any]) -> ToolErrorResponse:
        return ToolErrorResponse(
            error_code="MetricQueryError",
            error_message=str(exc),
            recovery_suggestion=(
                f"Metric query failed: {exc}. Please select from valid metric names: {list(self.SUPPORTED_METRICS)} "
                f"and valid monitored services: {list(self.MOCK_METRICS_DB.keys())}."
            ),
            valid_alternatives=list(self.SUPPORTED_METRICS),
        )
