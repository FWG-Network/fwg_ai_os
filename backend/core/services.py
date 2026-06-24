import redis
from qdrant_client import QdrantClient
from .config import settings

# ★★★ FIX: Centralized, shared clients ★★★
redis_client = redis.Redis(host=settings.REDIS_HOST, port=6379, db=0, decode_responses=True)
qdrant_client = QdrantClient(host=settings.QDRANT_HOST, port=6333)

# Setup Qdrant collection on startup if it doesn't exist
try:
    qdrant_client.recreate_collection(
        collection_name="aios_memory",
        vector_size=384, # all-MiniLM-L6-v2 produces 384-dim vectors
    )
    print("Qdrant collection 'aios_memory' created/recreated.")
except Exception as e:
    print(f"Qdrant collection 'aios_memory' likely already exists. Info: {e}")
