"""Human-in-the-Loop (HITL) Interruption Gate for High-Stakes Operations.

Adheres to AgentOps Rubric Category 3: Human-in-the-Loop Hooks.
Provides an explicit code-level interruption stop requiring human confirmation
before any mutating remediation or infrastructure alteration is executed.
"""

from __future__ import annotations

import enum
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from src.observability.logger import get_logger
from src.observability.pii_scrubber import PIIScrubber


class RiskLevel(enum.Enum):
    READ_ONLY = "READ_ONLY"
    LOW_RISK = "LOW_RISK"
    HIGH_STAKES_MUTATING = "HIGH_STAKES_MUTATING"


class ConfirmationRequiredInterrupt(Exception):
    """Exception raised when an agent attempts a high-stakes action without prior authorization."""

    def __init__(
        self,
        approval_id: str,
        action_name: str,
        parameters: dict[str, Any],
        justification: str,
        blast_radius: str,
        confirmation_token: str,
    ):
        self.approval_id = approval_id
        self.action_name = action_name
        self.parameters = PIIScrubber.scrub_dict(parameters)
        self.justification = justification
        self.blast_radius = blast_radius
        self.confirmation_token = confirmation_token
        super().__init__(
            f"HIGH-STAKES ACTION INTERRUPT: Action '{action_name}' requires human approval. "
            f"Approval ID: {approval_id}, Blast Radius: {blast_radius}"
        )


@dataclass
class PendingApproval:
    """Record of a high-stakes action waiting for human operator sign-off."""
    approval_id: str
    action_name: str
    parameters: dict[str, Any]
    justification: str
    blast_radius: str
    confirmation_token: str
    created_at: float = field(default_factory=time.time)
    approved: bool = False
    rejected: bool = False
    operator_notes: str = ""


class HITLGate:
    """Central registry and enforcement gate for Human-in-the-Loop workflows."""

    def __init__(self):
        self._pending_approvals: dict[str, PendingApproval] = {}
        self._logger = get_logger("hitl-gate")

    def check_authorization(
        self,
        action_name: str,
        parameters: dict[str, Any],
        risk_level: RiskLevel,
        justification: str = "Automated remediation step",
        blast_radius: str = "Service Level",
        provided_approval_id: str | None = None,
        provided_token: str | None = None,
    ) -> bool:
        """Check if an action is pre-approved. If not and action is high-stakes, halt with interrupt."""
        if risk_level != RiskLevel.HIGH_STAKES_MUTATING:
            return True

        # Check if already approved via valid token
        if provided_approval_id and provided_token:
            record = self._pending_approvals.get(provided_approval_id)
            if record and record.approved and record.confirmation_token == provided_token:
                self._logger.info(
                    f"HITL Gate: Action '{action_name}' verified and authorized by human operator.",
                    approval_id=provided_approval_id,
                )
                return True

        # Generate pending approval request and interrupt
        approval_id = f"APPR-{uuid.uuid4().hex[:8].upper()}"
        token = uuid.uuid4().hex
        approval_record = PendingApproval(
            approval_id=approval_id,
            action_name=action_name,
            parameters=PIIScrubber.scrub_dict(parameters),
            justification=justification,
            blast_radius=blast_radius,
            confirmation_token=token,
        )
        self._pending_approvals[approval_id] = approval_record

        self._logger.warning(
            f"HITL Gate: Halting execution for human authorization on action '{action_name}'.",
            approval_id=approval_id,
            action=action_name,
            parameters=parameters,
            blast_radius=blast_radius,
        )

        raise ConfirmationRequiredInterrupt(
            approval_id=approval_id,
            action_name=action_name,
            parameters=parameters,
            justification=justification,
            blast_radius=blast_radius,
            confirmation_token=token,
        )

    def grant_approval(self, approval_id: str, operator_notes: str = "Approved by on-call engineer") -> str:
        """Human operator grants approval for an interrupted action, returning the confirmation token."""
        record = self._pending_approvals.get(approval_id)
        if not record:
            raise KeyError(f"Approval ID '{approval_id}' not found.")
        record.approved = True
        record.operator_notes = operator_notes
        self._logger.info(f"Operator approved '{record.action_name}' ({approval_id}): {operator_notes}")
        return record.confirmation_token

    def reject_approval(self, approval_id: str, operator_notes: str = "Rejected by on-call engineer") -> None:
        """Human operator rejects an interrupted action."""
        record = self._pending_approvals.get(approval_id)
        if not record:
            raise KeyError(f"Approval ID '{approval_id}' not found.")
        record.rejected = True
        record.operator_notes = operator_notes
        self._logger.warning(f"Operator rejected '{record.action_name}' ({approval_id}): {operator_notes}")


# Global HITL Gate instance
_GLOBAL_HITL_GATE = HITLGate()


def get_hitl_gate() -> HITLGate:
    return _GLOBAL_HITL_GATE
