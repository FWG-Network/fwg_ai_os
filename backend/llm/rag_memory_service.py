# backend/llm/rag_memory_service.py

import uuid
from qdrant_client import models
from backend.core.services import qdrant_client
from backend.llm.embedding_service import embedding_service

class RAGMemoryService:
    """
    Handles the storage and retrieval of semantic information in the
    Qdrant vector database.
    """
    COLLECTION_NAME = "aios_memory"

    def add(self, text: str, metadata: dict = None):
        """
        Encodes a text document and upserts it into the Qdrant collection.
        """
        if not qdrant_client:
            print("ERROR: Qdrant client not available. Cannot add to memory.")
            return

        print(f"RAG Memory: Encoding and adding document: '{text[:50]}...'")
        vector = embedding_service.encode(text)
        
        qdrant_client.upsert(
            collection_name=self.COLLECTION_NAME,
            points=[
                models.PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector.tolist(),
                    payload={"text": text, "metadata": metadata or {}}
                )
            ]
        )
        print("RAG Memory: Document added to Qdrant.")

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        """
        Encodes a query and performs a semantic search against the Qdrant collection.
        """
        if not qdrant_client:
            print("ERROR: Qdrant client not available. Cannot search memory.")
            return []
        
        query_vector = embedding_service.encode(query)
        
        search_result = qdrant_client.search(
            collection_name=self.COLLECTION_NAME,
            query_vector=query_vector,
            limit=top_k,
            with_payload=True
        )
        
        # Format the results into a clean list of dictionaries
        return [
            {
                "score": hit.score,
                "text": hit.payload.get("text")
            }
            for hit in search_result
        ]

rag_memory_service = RAGMemoryService()
