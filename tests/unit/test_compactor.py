"""Unit tests for History Compaction and Persistent Session Store."""

from __future__ import annotations

import unittest
from src.memory.compactor import ContextCompactor
from src.memory.session_store import SessionStore


class TestCompactorSuite(unittest.TestCase):
    """Test cases verifying History Compaction and Context Management."""

    def setUp(self):
        self.store = SessionStore(":memory:")
        self.compactor = ContextCompactor(
            session_store=self.store,
            max_context_tokens=1000,
            compaction_threshold_tokens=200,
            keep_recent_turns=2,
        )

    def test_compaction_triggers_when_threshold_exceeded(self):
        session_id = "test-session-compact"
        
        # Add 6 turns that exceed the 200 token threshold
        for i in range(6):
            self.store.add_turn(
                session_id=session_id,
                role="user" if i % 2 == 0 else "assistant",
                content=f"Turn message {i} with substantial detailed diagnostic information about node failure {i} " * 5,
                token_count=50,
            )

        compacted = self.compactor.get_compacted_context(session_id)
        
        # Should return 1 system summary turn + 2 recent turns = 3 total turns
        self.assertEqual(len(compacted), 3)
        self.assertEqual(compacted[0]["role"], "system")
        self.assertIn("COMPACTED INCIDENT CONTEXT", compacted[0]["content"])
        self.assertIn("Turn message 5", compacted[-1]["content"])


if __name__ == "__main__":
    unittest.main()
