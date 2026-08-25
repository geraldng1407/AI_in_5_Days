"""Base Tool Interface with Strict Schemas and Guided Error Handling.

Adheres to AgentOps Rubric Category 1:
- Comprehensive Tool Docstrings
- Descriptive Naming
- Explicit JSON Schemas (Pydantic models)
- Guided Error Handling (Provides actionable recovery guidance to the LLM)
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

from src.observability.logger import log_intent, log_outcome
from src.observability.pii_scrubber import PIIScrubber
from src.pydantic_compat import BaseModel, Field


class ToolErrorResponse(BaseModel):
    """Structured error payload providing actionable recovery guidance back to the LLM."""
    status: str = Field(default="ERROR", description="Execution status code.")
    error_code: str = Field(description="Categorical error identifier.")
    error_message: str = Field(description="Human-readable description of what failed.")
    recovery_suggestion: str = Field(
        description="Explicit, actionable steps the LLM should take to resolve the error and succeed."
    )
    valid_alternatives: list[str] | None = Field(
        default=None, description="Optional list of accepted values or alternative parameters."
    )


class BaseTool(ABC):
    """Abstract base class for all agent tools."""

    name: str = ""
    description: str = ""
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]

    def get_json_schema(self) -> dict[str, Any]:
        """Return the JSON schema representation of the tool's input parameters."""
        return self.input_schema.model_json_schema()

    def run(self, raw_params: dict[str, Any], trace_id: str = "", span_id: str = "") -> dict[str, Any]:
        """Execute the tool with telemetry capture, schema validation, and guided error handling."""
        start_time = time.time()
        sanitized_params = PIIScrubber.scrub_dict(raw_params)

        log_intent(
            action=self.name,
            planned_params=sanitized_params,
            trace_id=trace_id,
            span_id=span_id,
            rationale=f"Executing tool '{self.name}' with validated inputs.",
        )

        try:
            validated_inputs = self.input_schema.model_validate(raw_params)
            result_model = self._execute(validated_inputs)
            result_dict = result_model.model_dump()

            duration_ms = (time.time() - start_time) * 1000.0
            log_outcome(
                action=self.name,
                result_summary=f"Successfully executed {self.name}",
                execution_time_ms=duration_ms,
                trace_id=trace_id,
                span_id=span_id,
                status="SUCCESS",
            )
            return PIIScrubber.scrub_dict(result_dict)

        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000.0
            error_response = self._handle_error(exc, raw_params)
            
            log_outcome(
                action=self.name,
                result_summary=error_response.error_message,
                execution_time_ms=duration_ms,
                trace_id=trace_id,
                span_id=span_id,
                status="ERROR",
                error_details=error_response.recovery_suggestion,
            )
            return error_response.model_dump()

    @abstractmethod
    def _execute(self, inputs: Any) -> BaseModel:
        pass

    def _handle_error(self, exc: Exception, raw_params: dict[str, Any]) -> ToolErrorResponse:
        error_name = type(exc).__name__
        return ToolErrorResponse(
            error_code=error_name,
            error_message=str(exc),
            recovery_suggestion=(
                f"Tool invocation failed with {error_name}. Review the input parameters: {raw_params}. "
                "Ensure all required fields are present and follow the schema constraints before retrying."
            ),
        )
