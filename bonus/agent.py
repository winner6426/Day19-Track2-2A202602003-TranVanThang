"""Minimal vector-store + feature-store memory agent."""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from qdrant_client import QdrantClient, models
from rank_bm25 import BM25Okapi

from app.embeddings import Embedder

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FEAST_REPO = ROOT / "app" / "feast_repo"
COLLECTION = "bonus_episodic_memory"
PROFILE_FEATURES = [
    "user_profile_features:reading_speed_wpm",
    "user_profile_features:preferred_language",
    "user_profile_features:topic_affinity",
    "query_velocity_features:queries_last_hour",
    "query_velocity_features:distinct_topics_24h",
]


class HybridMemoryAgent:
    """Recall episodic text from Qdrant and enrich it with Feast features."""

    def __init__(
        self,
        feature_store: Any | None = None,
        client: QdrantClient | None = None,
        embedder: Embedder | None = None,
        *,
        reset: bool = True,
        top_k: int = 3,
    ) -> None:
        self.client = client or QdrantClient(":memory:")
        self.embedder = embedder or Embedder()
        self.top_k = top_k
        self._memories: dict[str, dict[str, str]] = {}

        if feature_store is None:
            from feast import FeatureStore

            feature_store = FeatureStore(repo_path=str(DEFAULT_FEAST_REPO))
        self.feature_store = feature_store

        existing = {c.name for c in self.client.get_collections().collections}
        if reset and COLLECTION in existing:
            self.client.delete_collection(COLLECTION)
            existing.remove(COLLECTION)
        if COLLECTION not in existing:
            self.client.create_collection(
                collection_name=COLLECTION,
                vectors_config=models.VectorParams(
                    size=self.embedder.dim, distance=models.Distance.COSINE
                ),
            )

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return re.findall(r"\w+", text.lower(), flags=re.UNICODE)

    @classmethod
    def _chunk(cls, text: str, max_words: int = 80) -> list[str]:
        """Prefer sentence boundaries, then enforce a small context-safe cap."""
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        chunks: list[str] = []
        current: list[str] = []
        for sentence in sentences:
            words = sentence.split()
            if current and len(current) + len(words) > max_words:
                chunks.append(" ".join(current))
                current = current[-12:]  # small overlap preserves boundary context
            while len(words) > max_words:
                chunks.append(" ".join(words[:max_words]))
                words = words[max_words - 12 :]
            current.extend(words)
        if current:
            chunks.append(" ".join(current))
        return chunks or [text.strip()]

    def remember(self, text: str, user_id: str = "u_001") -> None:
        """Chunk, embed, and upsert one episodic memory for this user."""
        if not text.strip():
            raise ValueError("memory text must not be empty")
        chunks = self._chunk(text)
        vectors = list(self.embedder.embed(chunks))
        now = datetime.now(timezone.utc).isoformat()
        points = []
        for chunk, vector in zip(chunks, vectors):
            memory_id = str(uuid.uuid4())
            payload = {"user_id": user_id, "text": chunk, "created_at": now}
            self._memories[memory_id] = payload
            points.append(models.PointStruct(id=memory_id, vector=vector.tolist(), payload=payload))
        self.client.upsert(collection_name=COLLECTION, points=points)

    def _profile(self, user_id: str) -> dict[str, Any]:
        try:
            raw = self.feature_store.get_online_features(
                features=PROFILE_FEATURES,
                entity_rows=[{"user_id": user_id}],
            ).to_dict()
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                "Feast profile unavailable. Run notebook 04 or `feast apply` + "
                "`feast materialize-incremental` in app/feast_repo."
            ) from exc
        return {name.split(":")[-1]: (raw.get(name.split(":")[-1]) or [None])[0]
                for name in PROFILE_FEATURES}

    def _retrieve(self, query: str, user_id: str) -> list[tuple[float, str]]:
        candidates = {mid: row for mid, row in self._memories.items()
                      if row["user_id"] == user_id}
        if not candidates:
            return []

        user_filter = models.Filter(must=[models.FieldCondition(
            key="user_id", match=models.MatchValue(value=user_id)
        )])
        query_vector = next(self.embedder.embed([query])).tolist()
        semantic = self.client.query_points(
            collection_name=COLLECTION,
            query=query_vector,
            query_filter=user_filter,
            limit=min(15, len(candidates)),
        ).points

        ids = list(candidates)
        bm25 = BM25Okapi([self._tokenize(candidates[mid]["text"]) for mid in ids])
        lexical_scores = bm25.get_scores(self._tokenize(query))
        lexical = [ids[i] for i in sorted(range(len(ids)), key=lambda i: -lexical_scores[i])
                   if lexical_scores[i] > 0][:15]

        rrf: dict[str, float] = {}
        for rank, point in enumerate(semantic, start=1):
            rrf[str(point.id)] = rrf.get(str(point.id), 0.0) + 1 / (60 + rank)
        for rank, memory_id in enumerate(lexical, start=1):
            rrf[memory_id] = rrf.get(memory_id, 0.0) + 1 / (60 + rank)
        ranked = sorted(rrf, key=rrf.get, reverse=True)[: self.top_k]
        return [(rrf[mid], candidates[mid]["text"]) for mid in ranked]

    def recall(self, query: str, user_id: str = "u_001") -> str:
        """Return LLM-ready context from Feast profile plus hybrid retrieval."""
        profile = self._profile(user_id)
        affinity = profile.get("topic_affinity") or "unknown"
        retrieval_query = query
        if any(term in query.lower() for term in ("recommend", "gợi ý", "summary")):
            retrieval_query = f"{query} {affinity}"
        memories = self._retrieve(retrieval_query, user_id)
        memory_lines = [f"  {i}. [{score:.4f}] {text}" for i, (score, text)
                        in enumerate(memories, start=1)] or ["  (không có memory phù hợp)"]
        return "\n".join([
            f"USER: {user_id}",
            f"QUESTION: {query}",
            ("PROFILE (Feast): language={preferred_language}, "
             "reading_speed={reading_speed_wpm} wpm, topic_affinity={topic_affinity}").format(**profile),
            ("RECENT (Feast): queries_last_hour={queries_last_hour}, "
             "distinct_topics_24h={distinct_topics_24h}").format(**profile),
            "TOP MEMORIES (Qdrant + BM25/RRF):",
            *memory_lines,
        ])
