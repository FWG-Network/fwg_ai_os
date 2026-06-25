# backend/llm/rag_pipeline.py

from .prompt_engine import PromptEngine
# ★★★ UPGRADE: Import the new, real RAG memory service ★★★
from .rag_memory_service import rag_memory_service

class RAGPipeline:
    def __init__(self):
        self.prompt_engine = PromptEngine()
        self.retriever = rag_memory_service # Use the real service instance

    def build_prompt(self, query: str, system_prompt: str) -> str:
        """Builds a context-rich prompt using the real RAG service."""
        # 1. Retrieve relevant context from Qdrant
        retrieved_hits = self.retriever.search(query)
        context = "\n".join([hit['text'] for hit in retrieved_hits])
        
        if not context:
            context = "No relevant context found in memory."
        
        # 2. Build the final prompt
        return self.prompt_engine.build(system_prompt, context, query)

# This instance is now created in core/services.py
