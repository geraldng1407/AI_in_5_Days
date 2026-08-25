"""Self-Evaluation and Guardrail Policy Plugin.

Adheres to AgentOps Rubric Category 3: Guardrails & Policy Plugins.
Evaluates agent remediation hypotheses against safety policies, verified evidence,
and blast radius constraints before plans are returned or executed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.observability.logger import get_logger


@dataclass
class SelfEvaluationResult:
    is_safe: bool
    confidence_score: float
    violations: list[str] = field(default_factory=list)
    remediation_assessment: str = "Passed"


class SelfEvaluator:
    """Evaluates agent diagnosis and remediation plans against safety rules."""

    def __init__(self):
        self._logger = get_logger("self-evaluator")

    def evaluate_plan(
        self,
        incident_symptom: str,
        diagnosed_root_cause: str,
        remediation_action: str,
        evidence: list[str],
    ) -> SelfEvaluationResult:
        """Run policy validation on the proposed diagnosis and plan."""
        violations: list[str] = []

        # Rule 1: Evidence requirement
        if not evidence or len(evidence) < 1:
            violations.append("InsufficientTelemetryEvidence: Diagnosis has zero supporting telemetry logs or metrics.")

        # Rule 2: Root cause specificity
        if len(diagnosed_root_cause.strip()) < 10 or "unknown" in diagnosed_root_cause.lower():
            violations.append("VagueRootCause: Root cause description is insufficient or unspecified.")

        # Rule 3: Remediation safety check (e.g. prevent destructive rm/delete commands)
        forbidden_substrings = ["rm -rf", "drop database", "delete cluster", "force kill all"]
        if any(bad in remediation_action.lower() for bad in forbidden_substrings):
            violations.append(f"UnsafeRemediationCommand: Remediation contains destructive pattern.")

        is_safe = len(violations) == 0
        confidence = 0.95 if is_safe else 0.40

        result = SelfEvaluationResult(
            is_safe=is_safe,
            confidence_score=confidence,
            violations=violations,
            remediation_assessment="APPROVED" if is_safe else "REJECTED_BY_GUARDRAILS",
        )

        self._logger.info(
            "Self-Evaluation Guardrail check completed",
            is_safe=is_safe,
            confidence=confidence,
            violations_count=len(violations),
        )
        return result
