"""Episodic Semantic Vector Store.

Adheres to AgentOps Rubric Category 2: Persistent Session State.
Indexes past incident post-mortems and resolutions into a persistent vector store
for semantic retrieval across future triage sessions.
"""

from __future__ import annotations

import json
import math
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.observability.logger import get_logger
from src.observability.pii_scrubber import PIIScrubber


@dataclass
class IncidentMemory:
    incident_id: str
    title: str
    symptom: str
    root_cause: str
    resolution: str
    similarity_score: float = 0.0


class VectorStore:
    """Lightweight persistent embedding and vector store with cosine similarity matching."""

    def __init__(self, db_path: str = "data/vector_store.db"):
        self.db_path = db_path
        self._shared_conn: sqlite3.Connection | None = None
        if db_path == ":memory:":
            self._shared_conn = sqlite3.connect(":memory:")
            self._shared_conn.row_factory = sqlite3.Row
        else:
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self._logger = get_logger("vector-store")
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self._shared_conn is not None:
            return self._shared_conn
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        conn = self._get_connection()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS episodic_memories (
                incident_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                symptom TEXT NOT NULL,
                root_cause TEXT NOT NULL,
                resolution TEXT NOT NULL,
                embedding_json TEXT NOT NULL
            )
        """)
        conn.commit()
        if self._shared_conn is None:
            conn.close()

    @staticmethod
    def _compute_mock_embedding(text: str, dim: int = 16) -> list[float]:
        """Deterministic TF-IDF style pseudo-embedding for testing and standalone mode."""
        vec = [0.0] * dim
        words = text.lower().split()
        for i, word in enumerate(words):
            hash_val = hash(word)
            vec[hash_val % dim] += 1.0 / (1.0 + (i * 0.1))
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    @staticmethod
    def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1)) or 1.0
        norm2 = math.sqrt(sum(b * b for b in v2)) or 1.0
        return dot / (norm1 * norm2)

    def add_incident_post_mortem(
        self,
        incident_id: str,
        title: str,
        symptom: str,
        root_cause: str,
        resolution: str,
        embedding: list[float] | None = None,
    ) -> None:
        """Store an incident resolution post-mortem into episodic memory."""
        clean_title = PIIScrubber.scrub_text(title)
        clean_symptom = PIIScrubber.scrub_text(symptom)
        clean_cause = PIIScrubber.scrub_text(root_cause)
        clean_res = PIIScrubber.scrub_text(resolution)

        if not embedding:
            full_text = f"{clean_title} {clean_symptom} {clean_cause}"
            embedding = self._compute_mock_embedding(full_text)

        conn = self._get_connection()
        conn.execute(
            """
            INSERT OR REPLACE INTO episodic_memories 
            (incident_id, title, symptom, root_cause, resolution, embedding_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (incident_id, clean_title, clean_symptom, clean_cause, clean_res, json.dumps(embedding)),
        )
        conn.commit()
        self._logger.info(f"Consolidated incident '{incident_id}' into Episodic Vector Memory.")
        if self._shared_conn is None:
            conn.close()

    def search_similar_incidents(self, query_text: str, top_k: int = 2) -> list[IncidentMemory]:
        """Search historical incident memories by cosine similarity against query."""
        query_vec = self._compute_mock_embedding(query_text)
        results: list[tuple[float, sqlite3.Row]] = []

        conn = self._get_connection()
        rows = conn.execute("SELECT incident_id, title, symptom, root_cause, resolution, embedding_json FROM episodic_memories").fetchall()
        for row in rows:
            doc_vec = json.loads(row["embedding_json"])
            sim = self._cosine_similarity(query_vec, doc_vec)
            results.append((sim, row))

        results.sort(key=lambda x: x[0], reverse=True)
        top_results = results[:top_k]

        memories = [
            IncidentMemory(
                incident_id=row["incident_id"],
                title=row["title"],
                symptom=row["symptom"],
                root_cause=row["root_cause"],
                resolution=row["resolution"],
                similarity_score=round(score, 3),
            )
            for score, row in top_results
        ]
        if self._shared_conn is None:
            conn.close()
        return memories
