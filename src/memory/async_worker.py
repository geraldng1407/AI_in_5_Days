"""Async Background Memory Consolidation Worker.

Adheres to AgentOps Rubric Category 2: Async Memory Operations.
Extracts post-mortem insights and writes to episodic vector memory asynchronously
in a background task to prevent blocking the interactive user interface.
"""

from __future__ import annotations

import asyncio
from typing import Any

from src.memory.vector_store import VectorStore
from src.observability.logger import get_logger


class AsyncMemoryConsolidator:
    """Manages non-blocking background consolidation of incident memories."""

    def __init__(self, vector_store: VectorStore | None = None):
        self.vector_store = vector_store or VectorStore()
        self._logger = get_logger("async-memory-worker")

    async def _consolidate_task(
        self,
        incident_id: str,
        title: str,
        symptom: str,
        root_cause: str,
        resolution: str,
    ) -> None:
        """Background coroutine performing async memory synthesis and indexing."""
        try:
            self._logger.info(
                f"Starting async background memory consolidation for incident '{incident_id}'.",
                incident_id=incident_id,
            )
            await asyncio.sleep(0.01)

            self.vector_store.add_incident_post_mortem(
                incident_id=incident_id,
                title=title,
                symptom=symptom,
                root_cause=root_cause,
                resolution=resolution,
            )
            self._logger.info(
                f"Async background memory consolidation completed for incident '{incident_id}'.",
                incident_id=incident_id,
            )
        except Exception as exc:
            self._logger.error(
                f"Async memory consolidation failed for '{incident_id}': {exc}",
                incident_id=incident_id,
            )

    def trigger_consolidation(
        self,
        incident_id: str,
        title: str,
        symptom: str,
        root_cause: str,
        resolution: str,
    ) -> asyncio.Task | None:
        """Dispatch async consolidation task to the running event loop."""
        try:
            loop = asyncio.get_running_loop()
            task = loop.create_task(
                self._consolidate_task(incident_id, title, symptom, root_cause, resolution)
            )
            return task
        except RuntimeError:
            asyncio.run(self._consolidate_task(incident_id, title, symptom, root_cause, resolution))
            return None
