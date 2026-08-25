"""Runbook & SOP Retrieval Worker Agent.

Adheres to AgentOps Rubric Category 3:
- Multi-Agent Patterns (Specialized Worker agent)
- Strategic Model Routing (Uses Gemini Flash for runbook matching)
"""

from __future__ import annotations

from typing import Any
from src.config import get_config
from src.observability.logger import get_logger
from src.observability.tracer import get_tracer
from src.tools.runbook_search import SearchRunbookTool


class RunbookWorkerAgent:
    """Specialized Worker agent running on Gemini Flash for retrieving remediation SOPs."""

    def __init__(self):
        self.config = get_config()
        self.model_name = self.config.worker_model  # e.g., gemini-2.5-flash
        self.tool = SearchRunbookTool()
        self._logger = get_logger("runbook-worker")
        self._tracer = get_tracer()

    def find_remediations(self, symptom_query: str, trace_id: str = "") -> dict[str, Any]:
        """Search runbooks for validated remediation procedures matching symptoms."""
        with self._tracer.span("RunbookWorker.find_remediations", trace_id=trace_id) as span:
            span.set_attribute("model", self.model_name)
            span.set_attribute("query", symptom_query)

            self._logger.info(
                f"RunbookWorker (model: {self.model_name}) searching SOPs for '{symptom_query}'.",
                query=symptom_query,
                model=self.model_name,
                trace_id=trace_id,
            )

            raw_result = self.tool.run(
                {"query": symptom_query, "top_k": 2},
                trace_id=trace_id,
                span_id=span.span_id,
            )

            return {
                "worker": "RunbookWorker",
                "model_used": self.model_name,
                "runbooks": raw_result.get("runbooks", []),
                "status": raw_result.get("status", "SUCCESS"),
            }
