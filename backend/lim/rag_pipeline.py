from .prompt_engine import PromptEngine
from backend.llm.rag_memory_service import rag_memory_service

class RAGPipeline:
    def __init__(self):
        self.prompt_engine = PromptEngine()
        self.retriever = rag_memory_service  # ✅ FIX: unified with real Qdrant memory

    def build_prompt(self, query: str, system_prompt: str) -> str:
        """Builds a context-rich prompt using RAG."""
        # 1. Retrieve relevant context from the real Qdrant-backed memory
        retrieved_hits = self.retriever.search(query)
        context = "\n".join([hit['text'] for hit in retrieved_hits]) if retrieved_hits else "No relevant context found in memory."

        # 2. Build the final prompt
        return self.prompt_engine.build(system_prompt, context, query)
