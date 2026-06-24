import redis
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from .config import settings

# --- Centralized, Shared Clients ---

# ★★★ FIX: Added error handling for robust connection ★★★
try:
    redis_client = redis.Redis(
        host=settings.REDIS_HOST, 
        port=6379, 
        db=0, 
        decode_responses=True
    )
    # Ping the server to ensure a connection is established.
    redis_client.ping()
    print("✅ Successfully connected to Redis.")
except redis.exceptions.ConnectionError as e:
    print(f"❌ CRITICAL ERROR: Could not connect to Redis at {settings.REDIS_HOST}. Please check the service. Error: {e}")
    # In a real app, you might exit or have a fallback.
    redis_client = None


try:
    qdrant_client = QdrantClient(host=settings.QDRANT_HOST, port=6333)
    # The client initializes instantly, but we can check the connection by listing collections.
    qdrant_client.get_collections()
    print("✅ Successfully connected to Qdrant.")
except Exception as e:
    print(f"❌ CRITICAL ERROR: Could not connect to Qdrant at {settings.QDRANT_HOST}. Please check the service. Error: {e}")
    qdrant_client = None

# --- Idempotent Setup Logic ---

def setup_vector_database():
    """
    Ensures that the required Qdrant collection exists.
    This function is safe to run multiple times.
    """
    if not qdrant_client:
        print("Cannot setup vector database because Qdrant client is not available.")
        return

    collection_name = "aios_memory"
    try:
        collections = qdrant_client.get_collections().collections
        collection_names = [collection.name for collection in collections]

        # ★★★ FIX: Check if the collection exists BEFORE trying to create it ★★★
        if collection_name not in collection_names:
            print(f"Collection '{collection_name}' not found. Creating it now...")
            qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE),
            )
            print(f"✅ Collection '{collection_name}' created successfully.")
        else:
            print(f"✅ Collection '{collection_name}' already exists. No action needed.")

    except Exception as e:
        print(f"❌ ERROR: An error occurred during Qdrant collection setup. Error: {e}")

# Run the setup logic once when the application starts.
# This logic will be imported and run by both API and Worker services,
# but it is safe because it's idempotent.
setup_vector_database()
