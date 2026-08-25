# Incident Triage & Cloud SRE

Autonomous multi-agent system that diagnoses cloud infrastructure alerts, analyzes telemetry, performs root-cause investigations, and safely orchestrates remediations with human-in-the-loop governance.

## Language

**Incident**:
An unplanned disruption, performance degradation, or anomaly in cloud infrastructure identified via alerts or user reports.
_Avoid_: Ticket, problem, outage report, issue

**Coordinator**:
The lead orchestration agent (Gemini Pro) responsible for decomposing the investigation, delegating sub-tasks to workers, synthesizing findings, and formulating remediation plans.
_Avoid_: Master, manager, root bot, supervisor

**Worker**:
A specialized domain sub-agent (Gemini Flash) that executes specific diagnostic routines, such as log filtering, metric aggregation, or runbook retrieval.
_Avoid_: Helper, slave, child agent, task runner

**Remediation**:
A structured action or command proposed to resolve an incident or restore normal operations.
_Avoid_: Fix, patch, workaround, quickfix

**High-Stakes Action**:
Any mutating or state-altering operation (e.g., service restart, traffic rerouting, cluster scaling, rollback) that could impact production availability and strictly mandates human authorization before execution.
_Avoid_: Destructive operation, write call, dangerous command

**Human-in-the-Loop (HITL) Gate**:
An explicit code-level interruption mechanism that halts execution and yields control to a human operator before performing a high-stakes action.
_Avoid_: Prompt, user check, pause modal

**Episodic Memory**:
Persistent semantic vector and relational storage capturing past incident trajectories, root-cause analyses, and post-mortem resolutions across sessions.
_Avoid_: Chat history, context cache, log archive

**Constitution**:
The foundational system prompt defining the agent's identity, operational principles, guardrails, and compliance boundaries.
_Avoid_: System prompt, preamble, ruleset

**Telemetry Probe**:
A read-only diagnostic tool for extracting logs, traces, or metrics from cloud observability endpoints.
_Avoid_: Data fetcher, logger, query tool
