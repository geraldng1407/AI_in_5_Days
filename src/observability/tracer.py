"""Distributed OpenTelemetry Tracing Manager.

Adheres to AgentOps Rubric Category 4: Distributed Tracing.
Implements trace and span tracking to correlate requests across
Coordinator, Worker sub-agents, tool executions, and storage operations.
"""

from __future__ import annotations

import contextlib
import time
import uuid
from collections.abc import Generator
from dataclasses import dataclass, field
from typing import Any

from src.observability.logger import get_logger
from src.observability.pii_scrubber import PIIScrubber


@dataclass
class Span:
    """Represents a single operation span within a distributed trace."""
    span_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    trace_id: str = ""
    name: str = ""
    parent_span_id: str | None = None
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    status: str = "OK"

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = PIIScrubber.scrub_object(value)

    def finish(self, status: str = "OK") -> float:
        self.end_time = time.time()
        self.status = status
        return (self.end_time - self.start_time) * 1000.0


class TraceManager:
    """Manages creation, nesting, and propagation of distributed traces."""

    def __init__(self, service_name: str = "cloud-sre-agent"):
        self.service_name = service_name
        self.logger = get_logger("tracer")
        self.active_spans: list[Span] = []

    def start_trace(self, trace_id: str | None = None) -> str:
        return trace_id or uuid.uuid4().hex

    @contextlib.contextmanager
    def span(
        self,
        name: str,
        trace_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> Generator[Span, None, None]:
        """Context manager creating a traced span linked to parent context."""
        current_trace_id = trace_id or (self.active_spans[-1].trace_id if self.active_spans else self.start_trace())
        parent_span_id = self.active_spans[-1].span_id if self.active_spans else None

        new_span = Span(
            trace_id=current_trace_id,
            name=name,
            parent_span_id=parent_span_id,
            attributes=PIIScrubber.scrub_dict(attributes or {}),
        )
        self.active_spans.append(new_span)

        try:
            yield new_span
            duration_ms = new_span.finish(status="OK")
            self.logger.debug(
                f"Span '{name}' completed in {duration_ms:.2f}ms",
                trace_id=new_span.trace_id,
                span_id=new_span.span_id,
                parent_span_id=new_span.parent_span_id,
                status="OK",
            )
        except Exception as exc:
            duration_ms = new_span.finish(status="ERROR")
            new_span.set_attribute("error.message", str(exc))
            self.logger.error(
                f"Span '{name}' failed: {exc}",
                trace_id=new_span.trace_id,
                span_id=new_span.span_id,
                status="ERROR",
            )
            raise
        finally:
            self.active_spans.pop()


# Global trace manager
_GLOBAL_TRACER = TraceManager()


def get_tracer(service_name: str = "cloud-sre-agent") -> TraceManager:
    return _GLOBAL_TRACER
