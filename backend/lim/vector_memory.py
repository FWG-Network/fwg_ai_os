"""
backend/lim/vector_memory.py
Real Qdrant vector memory — replaces numpy mock.
"""
from typing import List, Optional
from backend.core.config import settings
from backend.core.logger import log


class VectorMemory:
    """
    Qdrant-backed vector memory.
    Replaces mock numpy/random implementation.
    """

    def __init__(self):
        self._client = None

    # ── Lazy Qdrant client ────────────────────────────────────────────
    def _get_client(self):
        if self._client is None:
            try:
                from qdrant_client import QdrantClient
                self._client = QdrantClient(
                    host=settings.QDRANT_HOST,
                    port=settings.QDRANT_PORT,
                    timeout=10,
                )
                log.info(f"[VectorMemory] ✅ Qdrant connected → {settings.QDRANT_URL}")
            except Exception as e:
                log.error(f"[VectorMemory] Qdrant unavailable: {e}")
                raise
        return self._client

    # ── Ensure collection exists ──────────────────────────────────────
    def _ensure_collection(self, collection: str, vector_size: int = 384) -> None:
        from qdrant_client.models import Distance, VectorParams
        client = self._get_client()
        existing = [c.name for c in client.get_collections().collections]
        if collection not in existing:
            client.create_collection(
                collection_name=collection,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE,
                ),
            )
            log.info(f"[VectorMemory] Created collection '{collection}'")

    # ── Embed text (HuggingFace or fallback) ─────────────────────────
    def _embed(self, text: str) -> List[float]:
        """
        Real text embedding.
        Try HuggingFace sentence-transformers → fallback hash-based.
        """
        try:
            from sentence_transformers import SentenceTransformer
            model  = SentenceTransformer("all-MiniLM-L6-v2")
            vector = model.encode(text).tolist()
            return vector
        except ImportError:
            log.warning("[VectorMemory] sentence_transformers not installed — using hash embedding")
            return self._hash_embed(text)

    @staticmethod
    def _hash_embed(text: str, dim: int = 384) -> List[float]:
        """
        Deterministic hash-based embedding.
        Better than random — same text = same vector.
        """
        import hashlib, math
        h      = hashlib.sha256(text.encode()).hexdigest()
        vector = []
        for i in range(dim):
            seed = int(h[i % 64], 16) + i
            val  = math.sin(seed) * 10000
            vector.append(val - int(val))   # fractional part in [-1, 1]
        return vector

    # ── ADD ───────────────────────────────────────────────────────────
    def add(
        self,
        text:       str,
        metadata:   Optional[dict] = None,
        collection: str            = "fwg_content",
        doc_id:     Optional[str]  = None,
    ) -> str:
        """Add text + metadata to Qdrant."""
        import uuid
        from qdrant_client.models import PointStruct

        point_id = doc_id or str(uuid.uuid4())
        vector   = self._embed(text)

        self._ensure_collection(collection, len(vector))
        client = self._get_client()

        client.upsert(
            collection_name=collection,
            points=[PointStruct(
                id=point_id,
                vector=vector,
                payload={
                    "text":     text,
                    "metadata": metadata or {},
                },
            )],
        )
        log.info(f"[VectorMemory] Added id={point_id} to '{collection}'")
        return point_id

    # ── SEARCH ────────────────────────────────────────────────────────
    def search(
        self,
        query:      str,
        top_k:      int = 5,
        collection: str = "fwg_content",
        threshold:  float = 0.0,
    ) -> List[dict]:
        """Semantic search in Qdrant."""
        try:
            self._ensure_collection(collection)
            client = self._get_client()
            vector = self._embed(query)

            results = client.search(
                collection_name=collection,
                query_vector=vector,
                limit=top_k,
                score_threshold=threshold,
                with_payload=True,
            )

            output = [{
                "id":       str(r.id),
                "score":    round(r.score, 4),
                "text":     r.payload.get("text", ""),
                "metadata": r.payload.get("metadata", {}),
            } for r in results]

            log.info(f"[VectorMemory] search '{query[:40]}' → {len(output)} results")
            return output

        except Exception as e:
            log.error(f"[VectorMemory] Search failed: {e}")
            return []

    # ── DELETE ────────────────────────────────────────────────────────
    def delete(self, doc_id: str, collection: str = "fwg_content") -> bool:
        """Delete a point by ID."""
        try:
            from qdrant_client.models import PointIdsList
            self._get_client().delete(
                collection_name=collection,
                points_selector=PointIdsList(points=[doc_id]),
            )
            log.info(f"[VectorMemory] Deleted id={doc_id}")
            return True
        except Exception as e:
            log.error(f"[VectorMemory] Delete failed: {e}")
            return False

    # ── STATS ─────────────────────────────────────────────────────────
    def stats(self, collection: str = "fwg_content") -> dict:
        """Get collection stats."""
        try:
            info = self._get_client().get_collection(collection)
            return {
                "collection":    collection,
                "vectors_count": info.vectors_count,
                "status":        str(info.status),
            }
        except Exception as e:
            return {"collection": collection, "error": str(e)}


# ── Global instance ───────────────────────────────────────────────────
vector_memory_service = VectorMemory()

# ── Backward compat alias (old code used vector_memory_db) ───────────
vector_memory_db = vector_memory_service
