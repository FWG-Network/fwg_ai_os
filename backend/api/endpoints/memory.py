from fastapi import APIRouter, HTTPException
from typing import List

from backend.models.schemas import ContentItem
from backend.llm.rag_memory_service import rag_memory_service
from backend.core.logger import log

router = APIRouter()


@router.post("/add")
async def add_memory(item: ContentItem):
    """
    Stores a content item in the Knowledge Base (Qdrant vector memory).
    """
    log.info(f"Knowledge Base: Storing item '{item.text[:50]}...'")
    try:
        rag_memory_service.add(text=item.text, metadata=item.metadata)
        return {"status": "success"}
    except Exception as e:
        log.error(f"Failed to store item in knowledge base: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to store memory item: {e}")


@router.post("/search")
async def search_memory(query: str, top_k: int = 3) -> List[dict]:
    """
    Searches the Knowledge Base for relevant content items.
    """
    log.info(f"Knowledge Base: Searching for query: '{query}'")
    try:
        results = rag_memory_service.search(query=query, top_k=top_k)
        return results
    except Exception as e:
        log.error(f"Failed to search knowledge base: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to search memory: {e}")
