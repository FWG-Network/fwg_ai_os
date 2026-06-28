"""
backend/lim/rag_pipeline.py
RAG Pipeline — Retrieve → Augment → Generate
"""
from __future__ import annotations
from typing import Optional
from backend.core.logger import log


class RAGPipeline:
    """
    Retrieve-Augment-Generate pipeline.

    Flow:
      query → vector_memory.search() → build prompt → llm_router.generate() → response
    """

    def __init__(self):
        self._prompt_engine = None
        self._memory        = None
        self._llm_router    = None

    # ── Lazy singletons ───────────────────────────────────────────────
    @property
    def memory(self):
        if self._memory is None:
            # ✅ Fix: correct module path lim (not llm)
            from backend.lim.vector_memory import vector_memory_service
            self._memory = vector_memory_service
        return self._memory

    @property
    def prompt_engine(self):
        if self._prompt_engine is None:
            from backend.lim.prompt_engine import PromptEngine
            self._prompt_engine = PromptEngine()
        return self._prompt_engine

    @property
    def llm(self):
        if self._llm_router is None:
            from backend.lim.llm_router import llm_router
            self._llm_router = llm_router
        return self._llm_router

    # ── SEARCH context ────────────────────────────────────────────────
    def _retrieve_context(
        self,
        query:      str,
        top_k:      int = 5,
        collection: str = "fwg_content",
    ) -> str:
        """Retrieve relevant context from Qdrant."""
        try:
            hits = self.memory.search(
                query=query,
                top_k=top_k,
                collection=collection,
            )
            if not hits:
                return "No relevant context found in memory."

            context = "\n\n".join([
                f"[{i+1}] (score={h['score']:.3f}) {h['text']}"
                for i, h in enumerate(hits)
            ])
            log.info(f"[RAG] Retrieved {len(hits)} context chunks")
            return context

        except Exception as e:
            log.warning(f"[RAG] Context retrieval failed: {e}")
            return "Context unavailable."

    # ── BUILD PROMPT ──────────────────────────────────────────────────
    def build_prompt(
        self,
        query:         str,
        system_prompt: str = "You are a helpful AI assistant.",
        collection:    str = "fwg_content",
    ) -> str:
        """Build context-rich prompt for LLM."""
        context = self._retrieve_context(query, collection=collection)
        return self.prompt_engine.build(system_prompt, context, query)

    # ── QUERY (main entry point) ───────────────────────────────────────
    async def query(
        self,
        prompt:        str,
        system_prompt: str            = "You are a helpful AI assistant.",
        model:         Optional[str]  = None,
        max_tokens:    int            = 512,
        collection:    str            = "fwg_content",
    ) -> str:
        """
        Full RAG pipeline:
        1. Retrieve context from Qdrant
        2. Build augmented prompt
        3. Generate response via LLM
        """
        log.info(f"[RAG] query='{prompt[:60]}...' model={model}")

        # ── Step 1 + 2: Retrieve + Augment ────────────────────────────
        augmented_prompt = self.build_prompt(prompt, system_prompt, collection)

        # ── Step 3: Generate ──────────────────────────────────────────
        result = await self.llm.generate(
            prompt=augmented_prompt,
            model=model,
            max_tokens=max_tokens,
        )
        return result

    # ── ADD to memory ─────────────────────────────────────────────────
    def add_to_memory(
        self,
        text:       str,
        metadata:   Optional[dict] = None,
        collection: str            = "fwg_content",
    ) -> str:
        """Add text to Qdrant vector memory."""
        return self.memory.add(
            text=text,
            metadata=metadata,
            collection=collection,
        )


# ── Global instance ───────────────────────────────────────────────────
rag_pipeline = RAGPipeline()
