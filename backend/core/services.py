# ===================================================================
# CENTRAL SERVICE INITIALIZATION HUB
# This file is the single source of truth for all service instances.
# It prevents circular dependencies and ensures a clean startup order.
# ===================================================================
import redis
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from .config import settings

# --- Infrastructure Clients ---
print("Initializing core infrastructure clients...")
try:
    redis_client = redis.Redis(host=settings.REDIS_HOST, port=6379, db=0, decode_responses=True)
    redis_client.ping()
    print("✅ Redis client initialized.")
except Exception as e:
    print(f"❌ CRITICAL: Failed to connect to Redis. {e}")
    redis_client = None

try:
    qdrant_client = QdrantClient(host=settings.QDRANT_HOST, port=6333)
    qdrant_client.get_collections()
    print("✅ Qdrant client initialized.")
except Exception as e:
    print(f"❌ CRITICAL: Failed to connect to Qdrant. {e}")
    qdrant_client = None

# --- Application Service Classes ---
print("Importing service classes...")
# ★★★ FIX: Import only the classes that are truly independent ★★★
from backend.learning.reward import RewardEngine
from backend.learning.online_learning import OnlineLearning
# ... other independent services ...
from backend.learning.trainer import Trainer
from backend.aios.task_planner import TaskPlanner
from backend.aios.executor import Executor
from backend.aios.reflection import ReflectionEngine
from backend.aios.autonomous_loop import AutonomousLoop
from backend.services.discovery_engine import DiscoveryEngine
from backend.services.ranking_engine import RankingEngine
from backend.services.personalization_engine import PersonalizationEngine
from backend.services.multimodal_engine import MultimodalEngine
from backend.lim.orchestrator import LLMOrchestrator

# --- Singleton Service Instances ---
print("Instantiating INDEPENDENT singleton service instances...")
reward_service = RewardEngine()
online_learning_service = OnlineLearning()
# ★★★ FIX: All services are now created here ★★★
trainer_service = Trainer()
task_planner_service = TaskPlanner()
executor_service = Executor()
reflection_service = ReflectionEngine()
autonomous_loop_service = AutonomousLoop()
discovery_engine_service = DiscoveryEngine()
ranking_engine_service = RankingEngine()
personalization_engine_service = PersonalizationEngine()
multimodal_engine_service = MultimodalEngine()
llm_orchestrator_service = LLMOrchestrator()
print("✅ All application services instantiated.")


# --- Idempotent Setup Logic ---
def setup_vector_database():
    if not qdrant_client: return
    collection_name = "aios_memory"
    try:
        collections = qdrant_client.get_collections().collections
        if collection_name not in [c.name for c in collections]:
            qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE),
            )
            print(f"✅ Qdrant collection '{collection_name}' created.")
        else:
            print(f"✅ Qdrant collection '{collection_name}' already exists.")
    except Exception as e:
        print(f"❌ ERROR during Qdrant setup: {e}")

# Run setup on import
setup_vector_database()
