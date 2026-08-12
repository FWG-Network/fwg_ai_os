from backend.lim.vector_memory import vector_memory_service


class RAGMemoryService:
    def add(self, text: str, metadata: dict = None) -> str:
        return vector_memory_service.add(text=text, metadata=metadata)

    def search(self, query: str, top_k: int = 5) -> list:
        return vector_memory_service.search(query=query, top_k=top_k)


rag_memory_service = RAGMemoryService()
