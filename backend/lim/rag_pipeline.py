from .prompt_engine import PromptEngine
from .vector_memory import vector_memory_db

class RAGPipeline:
    def __init__(self):
        self.prompt_engine = PromptEngine()
        self.retriever = vector_memory_db

    def build_prompt(self, query: str, system_prompt: str) -> str:
        """Builds a context-rich prompt using RAG."""
        # 1. Retrieve relevant context
        retrieved_docs = self.retriever.search(query)
        context = "\n".join(retrieved_docs)
        
        # 2. Build the final prompt
        return self.prompt_engine.build(system_prompt, context, query)
