"""Unit tests for Human-in-the-Loop authorization gate."""

from __future__ import annotations

import unittest
from src.guardrails.hitl import ConfirmationRequiredInterrupt, HITLGate, RiskLevel


class TestHITLGate(unittest.TestCase):
    """Test cases verifying Human-in-the-Loop Hooks."""

    def setUp(self):
        self.gate = HITLGate()

    def test_read_only_action_passes_freely(self):
        result = self.gate.check_authorization(
            action_name="fetch_logs",
            parameters={"service": "checkout"},
            risk_level=RiskLevel.READ_ONLY,
        )
        self.assertTrue(result)

    def test_high_stakes_action_raises_interrupt_without_approval(self):
        with self.assertRaises(ConfirmationRequiredInterrupt) as ctx:
            self.gate.check_authorization(
                action_name="restart_production_pod",
                parameters={"service": "checkout", "pod": "pod-1"},
                risk_level=RiskLevel.HIGH_STAKES_MUTATING,
                blast_radius="Production Pod Restart",
            )
        
        self.assertTrue(ctx.exception.approval_id.startswith("APPR-"))
        self.assertEqual(ctx.exception.action_name, "restart_production_pod")

    def test_high_stakes_action_succeeds_with_human_token(self):
        # 1. Trigger interrupt to create pending record
        approval_id = None
        try:
            self.gate.check_authorization(
                action_name="rollback_deployment",
                parameters={"version": "v1.0"},
                risk_level=RiskLevel.HIGH_STAKES_MUTATING,
            )
        except ConfirmationRequiredInterrupt as exc:
            approval_id = exc.approval_id

        self.assertIsNotNone(approval_id)

        # 2. Grant human approval
        token = self.gate.grant_approval(approval_id, operator_notes="Approved for rollout")

        # 3. Verify execution succeeds with token
        authorized = self.gate.check_authorization(
            action_name="rollback_deployment",
            parameters={"version": "v1.0"},
            risk_level=RiskLevel.HIGH_STAKES_MUTATING,
            provided_approval_id=approval_id,
            provided_token=token,
        )
        self.assertTrue(authorized)


if __name__ == "__main__":
    unittest.main()
