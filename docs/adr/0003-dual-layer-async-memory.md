# Dual-Layer Persistence with Async Episodic Memory Consolidation

Single-session conversational state leads to context bloat and prevents the agent from learning from historical outages across triage sessions. We decided to split state management into a fast relational session store (tracking ongoing turns with sliding-window compaction) and a persistent vector store for long-term episodic memory, updated via non-blocking background `asyncio` consolidation tasks to extract post-mortem insights without blocking synchronous user interaction.
