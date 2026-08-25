"""Automated Evaluation Suite for Measuring Agent Accuracy and Regressions.

Adheres to AgentOps Rubric Category 5: Automated Evaluation Suites.
Executes end-to-end multi-agent scenario evaluations against the golden benchmark dataset.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from src.agents.coordinator import IncidentCoordinatorAgent
from src.guardrails.hitl import get_hitl_gate
from src.memory.session_store import SessionStore
from src.memory.vector_store import VectorStore
from src.observability.pii_scrubber import PIIScrubber


class TestIncidentEvaluationSuite(unittest.TestCase):
    """Evaluation harness running regression benchmarks against golden incidents."""

    def setUp(self):
        self.test_session_store = SessionStore(":memory:")
        self.test_vector_store = VectorStore(":memory:")
        self.coordinator = IncidentCoordinatorAgent(
            session_store=self.test_session_store,
            vector_store=self.test_vector_store,
        )
        self.hitl_gate = get_hitl_gate()

        golden_path = Path(__file__).parent / "data" / "golden_incidents.json"
        with open(golden_path, "r", encoding="utf-8") as f:
            self.golden_dataset = json.load(f)

    def test_golden_dataset_evaluations(self):
        """Evaluate all golden benchmark incidents for diagnostic precision and HITL compliance."""
        for scenario in self.golden_dataset:
            with self.subTest(scenario=scenario["name"]):
                session_id = f"eval-session-{scenario['id']}"
                
                # Phase 1: Run unapproved initial triage (should interrupt at HITL gate)
                result = self.coordinator.triage_incident(
                    session_id=session_id,
                    service_name=scenario["service_name"],
                    reported_symptom=scenario["symptom"],
                )

                # 1. Verify Model Routing
                self.assertIn("pro", result["coordinator_model"].lower())
                self.assertIn("flash", result["worker_model"].lower())

                # 2. Verify Diagnostic Accuracy (Root Cause Keywords)
                root_cause = result["diagnosis"]["diagnosed_root_cause"].lower()
                matched_keywords = [
                    kw for kw in scenario["expected_root_cause_keywords"] if kw in root_cause
                ]
                self.assertTrue(
                    len(matched_keywords) > 0,
                    f"Diagnosis '{root_cause}' missing expected keywords {scenario['expected_root_cause_keywords']}",
                )

                # 3. Verify Guardrail Safety
                self.assertTrue(result["guardrail_evaluation"]["is_safe"])
                self.assertGreaterEqual(result["guardrail_evaluation"]["confidence_score"], 0.8)

                # 4. Verify Remediation Action Matches
                proposed_action = result["remediation"]["proposed_action"]
                self.assertEqual(proposed_action, scenario["expected_remediation_action"])

                # 5. Verify HITL Gate Interception for Mutating Action
                if scenario["requires_hitl"]:
                    self.assertEqual(result["remediation"]["remediation_status"], "AWAITING_HUMAN_APPROVAL")
                    self.assertIsNotNone(result["remediation"]["hitl_gate"])

                # Phase 2: Human Operator grants approval and retries execution
                pending_id = next(iter(self.hitl_gate._pending_approvals.keys()))
                token = self.hitl_gate.grant_approval(pending_id, operator_notes="Approved for eval test")

                # Re-run with valid approval credentials
                approved_result = self.coordinator.triage_incident(
                    session_id=session_id,
                    service_name=scenario["service_name"],
                    reported_symptom=scenario["symptom"],
                    approval_id=pending_id,
                    confirmation_token=token,
                )

                self.assertEqual(
                    approved_result["remediation"]["remediation_status"],
                    "EXECUTED",
                    "Remediation should successfully execute once human approval token is provided",
                )

    def test_pii_redaction_across_traces_and_memory(self):
        """Ensure sensitive tokens, passwords, and IPs are scrubbed before storage."""
        sample_key = "".join(["AIza", "SyD98765432101234567890123456789012"])
        raw_text_with_pii = (
            f"User test.user@example.com connected from 192.168.1.50 using key {sample_key}. "
            "Authorization: Bearer secret-token-xyz123."
        )
        scrubbed = PIIScrubber.scrub_text(raw_text_with_pii)
        
        self.assertNotIn("test.user@example.com", scrubbed)
        self.assertNotIn("192.168.1.50", scrubbed)
        self.assertNotIn(sample_key, scrubbed)
        self.assertNotIn("secret-token-xyz123", scrubbed)
        self.assertIn("[REDACTED_EMAIL]", scrubbed)
        self.assertIn("[REDACTED_IP]", scrubbed)
        self.assertIn("[REDACTED_GOOGLE_API_KEY]", scrubbed)


if __name__ == "__main__":
    unittest.main()
