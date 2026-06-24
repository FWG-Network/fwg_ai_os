import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# In a real system, we'd use a dedicated Vector DB like Qdrant or Milvus.
# Here, we simulate it in-memory for demonstration.
class VectorMemory:
    def __init__(self):
        self.embeddings = []
        self.documents = []
        # Mock text encoder
        self.encoder = lambda text: np.random.rand(384).astype(np.float32)

    def add(self, text: str):
        """Encodes text and adds it to memory."""
        print(f"Adding to vector memory: '{text[:30]}...'")
        embedding = self.encoder(text)
        self.embeddings.append(embedding)
        self.documents.append(text)

    def search(self, query: str, top_k: int = 3) -> list:
        """Searches for the most relevant documents."""
        if not self.embeddings:
            return []
            
        query_embedding = self.encoder(query).reshape(1, -1)
        
        # Calculate cosine similarity
        scores = cosine_similarity(query_embedding, np.array(self.embeddings))[0]
        
        # Get top_k results
        top_indices = scores.argsort()[-top_k:][::-1]
        
        return [self.documents[i] for i in top_indices]

# Create a global instance and add some mock data
vector_memory_db = VectorMemory()
vector_memory_db.add("The Ranking Engine V8 uses multi-factor scoring including popularity and freshness.")
vector_memory_db.add("Phase 5 introduced a real-time feedback loop using Celery workers.")
vector_memory_db.add("User personalization is handled by the Profile and Interest Engine in Phase 4.")
