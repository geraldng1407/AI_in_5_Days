# Coordinator-Worker Architecture with Strategic Model Routing

Complex cloud incident triage requires both high-level root-cause reasoning and high-throughput diagnostic probe execution. We decided to implement a Coordinator-Worker multi-agent topology using Google GenAI SDK, where the lead Coordinator runs on Gemini Pro for multi-step reasoning, plan decomposition, and remediation synthesis, while specialized diagnostic Workers (log scraping, metric aggregation, runbook search) run on Gemini Flash for sub-second latency and low operational cost.
