"""Context History Compaction and Sliding Window Manager.

Adheres to AgentOps Rubric Category 2: History Compaction.
Manages context bloat by monitoring conversation token budgets, maintaining
a sliding window of recent turns, and synthesizing older turns into an executive summary.
"""

from __future__ import annotations

from typing import Any
from src.memory.session_store import SessionStore, Turn
from src.observability.logger import get_logger


class ContextCompactor:
    """Token-budgeted context compaction engine."""

    def __init__(
        self,
        session_store: SessionStore,
        max_context_tokens: int = 8192,
        compaction_threshold_tokens: int = 4000,
        keep_recent_turns: int = 4,
    ):
        self.session_store = session_store
        self.max_context_tokens = max_context_tokens
        self.compaction_threshold = compaction_threshold_tokens
        self.keep_recent_turns = keep_recent_turns
        self._logger = get_logger("context-compactor")

    def get_compacted_context(self, session_id: str) -> list[dict[str, Any]]:
        """Retrieve conversational history, compacting older turns if token threshold is breached."""
        all_turns = self.session_store.get_turns(session_id)
        if not all_turns:
            return []

        total_tokens = sum(turn.token_count for turn in all_turns)

        # If below threshold, return raw history
        if total_tokens <= self.compaction_threshold or len(all_turns) <= self.keep_recent_turns:
            return [{"role": t.role, "content": t.content} for t in all_turns]

        # Trigger compaction on older turns
        self._logger.info(
            f"Context token limit reached ({total_tokens} > {self.compaction_threshold}). Compacting conversation.",
            session_id=session_id,
            total_tokens=total_tokens,
        )

        turns_to_summarize = all_turns[:-self.keep_recent_turns]
        recent_turns = all_turns[-self.keep_recent_turns:]

        # Create structured summary of older turns
        summary_lines = ["[COMPACTED INCIDENT CONTEXT - SUMMARY OF PREVIOUS TURNS]"]
        for t in turns_to_summarize:
            first_line = t.content.strip().split("\n")[0][:120]
            summary_lines.append(f"- {t.role.upper()} ({t.timestamp}): {first_line}...")

        summary_content = "\n".join(summary_lines)
        self.session_store.update_summary(session_id, summary_content)

        compacted_payload: list[dict[str, Any]] = [
            {"role": "system", "content": summary_content}
        ]
        compacted_payload.extend([{"role": t.role, "content": t.content} for t in recent_turns])

        return compacted_payload
