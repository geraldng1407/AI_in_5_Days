"""Main Entrypoint and Interactive CLI for the Cloud SRE Multi-Agent System."""

from __future__ import annotations

import argparse
import json
import sys

from src.agents.coordinator import IncidentCoordinatorAgent
from src.config import get_config
from src.guardrails.hitl import get_hitl_gate
from src.observability.logger import get_logger


def main() -> None:
    parser = argparse.ArgumentParser(description="Cloud SRE Autonomous Multi-Agent Incident Triage CLI")
    parser.add_argument("--service", "-s", default="checkout-service", help="Target microservice under investigation")
    parser.add_argument("--symptom", "-m", default="500 Internal Server Error spike and elevated latency", help="Reported incident symptom")
    parser.add_argument("--session-id", default="cli-session-001", help="Session identifier for multi-turn context")
    parser.add_argument("--approve", help="Approval ID to authorize a pending high-stakes remediation")
    parser.add_argument("--token", help="Confirmation token corresponding to the approval ID")

    args = parser.parse_args()
    logger = get_logger("main")
    config = get_config()

    print("=" * 80)
    print("🚀 Cloud SRE Multi-Agent Incident Triage System")
    print(f"📌 Coordinator Model: {config.coordinator_model} | Worker Model: {config.worker_model}")
    print("=" * 80)

    coordinator = IncidentCoordinatorAgent()
    hitl_gate = get_hitl_gate()

    if args.approve and not args.token:
        # Operator wants to approve via CLI
        token = hitl_gate.grant_approval(args.approve, operator_notes="Approved via CLI parameter")
        print(f"\n✅ Granted approval for {args.approve}. Generated confirmation token: {token}\n")
        args.token = token

    print(f"\n🔍 Initiating multi-agent investigation on '{args.service}'...")
    result = coordinator.triage_incident(
        session_id=args.session_id,
        service_name=args.service,
        reported_symptom=args.symptom,
        approval_id=args.approve,
        confirmation_token=args.token,
    )

    print("\n📋 INCIDENT BRIEFING & DIAGNOSTIC REPORT:")
    print(json.dumps(result, indent=2))

    remediation = result.get("remediation", {})
    if remediation.get("remediation_status") == "AWAITING_HUMAN_APPROVAL":
        print("\n⚠️  [HITL GATE PAUSE] Mutating remediation requires human authorization.")
        hitl_info = remediation.get("hitl_gate", {})
        print(f"👉 Action: {remediation.get('proposed_action')}")
        print(f"👉 Approval ID: {hitl_info.get('approval_id') or 'See pending approvals'}")
        print(f"👉 Run with --approve <APPROVAL_ID> to authorize execution.")
    else:
        print("\n✅ [REMEDIATION EXECUTED] Incident mitigations successfully applied.")


if __name__ == "__main__":
    main()
