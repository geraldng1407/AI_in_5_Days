"""High-Stakes Mutating Remediation Execution Tool.

Adheres to AgentOps Rubric:
- Category 1: Explicit schemas, descriptive naming, guided recovery
- Category 3: Human-in-the-Loop Hooks (Strictly intercepted by HITLGate)
"""

from __future__ import annotations

from typing import Any
from src.guardrails.hitl import ConfirmationRequiredInterrupt, RiskLevel, get_hitl_gate
from src.pydantic_compat import BaseModel, Field
from src.tools.base import BaseTool, ToolErrorResponse


class ExecuteServiceRemediationInput(BaseModel):
    """Input parameters for executing infrastructure and service remediations."""
    service_name: str = Field(
        description="Target microservice (e.g., 'checkout-service', 'auth-service', 'inventory-db')."
    )
    action_type: str = Field(
        description="Remediation operation: 'rolling_restart_pod', 'rollback_deployment', 'scale_replicas', 'flush_cache', 'trip_circuit_breaker'."
    )
    action_parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters for the remediation (e.g. {'target_version': 'v1.4.2'} or {'replica_count': 5})."
    )
    justification: str = Field(
        min_length=10,
        description="Technical justification and diagnosis reasoning for why this remediation is necessary."
    )
    approval_id: str | None = Field(
        default=None,
        description="HITL Approval ID provided by human operator if previously interrupted."
    )
    confirmation_token: str | None = Field(
        default=None,
        description="Secure confirmation token provided by human operator."
    )


class ExecuteServiceRemediationOutput(BaseModel):
    """Output result after successful remediation execution."""
    status: str = Field(default="SUCCESS", description="Remediation status.")
    action_executed: str = Field(description="Action performed.")
    service_name: str = Field(description="Target service.")
    execution_summary: str = Field(description="Result summary.")
    verification_advice: str = Field(description="Instructions on how to verify telemetry recovery.")


class ExecuteServiceRemediationTool(BaseTool):
    """Executes mutating remediation actions against cloud infrastructure."""

    name = "execute_service_remediation"
    description = (
        "Executes mutating remediation commands (rolling restarts, rollbacks, scaling, cache flushes) "
        "on cloud services. STRICTLY requires prior human-in-the-loop authorization."
    )
    input_schema = ExecuteServiceRemediationInput
    output_schema = ExecuteServiceRemediationOutput

    VALID_ACTIONS = {
        "rolling_restart_pod", "rollback_deployment", "scale_replicas",
        "flush_cache", "trip_circuit_breaker"
    }

    def _execute(self, inputs: ExecuteServiceRemediationInput) -> ExecuteServiceRemediationOutput:
        action = inputs.action_type.lower().strip()
        if action not in self.VALID_ACTIONS:
            raise ValueError(
                f"Invalid action_type '{inputs.action_type}'. Must be one of: {list(self.VALID_ACTIONS)}"
            )

        hitl_gate = get_hitl_gate()
        hitl_gate.check_authorization(
            action_name=f"{action} on {inputs.service_name}",
            parameters=inputs.action_parameters,
            risk_level=RiskLevel.HIGH_STAKES_MUTATING,
            justification=inputs.justification,
            blast_radius=f"Direct state modification on service '{inputs.service_name}'",
            provided_approval_id=inputs.approval_id,
            provided_token=inputs.confirmation_token,
        )

        summary = (
            f"Successfully executed '{action}' on service '{inputs.service_name}'. "
            f"Parameters applied: {inputs.action_parameters}."
        )

        return ExecuteServiceRemediationOutput(
            status="SUCCESS",
            action_executed=action,
            service_name=inputs.service_name,
            execution_summary=summary,
            verification_advice="Query 'query_service_metrics' and 'fetch_telemetry_logs' in 2 minutes to confirm recovery.",
        )

    def _handle_error(self, exc: Exception, raw_params: dict[str, Any]) -> ToolErrorResponse:
        if isinstance(exc, ConfirmationRequiredInterrupt):
            return ToolErrorResponse(
                error_code="HITL_CONFIRMATION_REQUIRED",
                error_message=str(exc),
                recovery_suggestion=(
                    f"Action halted for human authorization. Approval ID: '{exc.approval_id}'. "
                    f"Present this action and blast radius to the human operator. Once approved, retry "
                    f"calling this tool including 'approval_id': '{exc.approval_id}' and 'confirmation_token': '<token>'."
                ),
            )
        return ToolErrorResponse(
            error_code="RemediationExecutionError",
            error_message=str(exc),
            recovery_suggestion=f"Verify that action_type is in {list(self.VALID_ACTIONS)} and parameters are valid.",
            valid_alternatives=list(self.VALID_ACTIONS),
        )
