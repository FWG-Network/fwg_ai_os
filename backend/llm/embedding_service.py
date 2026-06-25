# backend/llm/embedding_service.py

from sentence_transformers import SentenceTransformer
import torch
import gc

class EmbeddingService:
    """
    A singleton service responsible for loading and using the sentence embedding model.
    This ensures the model is loaded into memory only once.
    """
    def __init__(self):
        print("Initializing EmbeddingService...")
        # Check for CUDA availability, fallback to CPU
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"EmbeddingService: Using device '{device}'.")
        
        # Load the pre-trained model. This will be shared in memory by forked processes.
        self.model = SentenceTransformer('all-MiniLM-L6-v2', device=device)
        
        # Set to evaluation mode for inference
        self.model.eval()
        
        print("✅ EmbeddingService: Sentence Transformer model loaded and set to eval mode.")

    def encode(self, text: str | list[str]):
        """
        Encodes a single text or a list of texts into semantic embeddings.
        This operation is wrapped in torch.no_grad() for performance.
        """
        with torch.no_grad():
            embeddings = self.model.encode(text, convert_to_tensor=False)
        return embeddings

# Instantiate the service once at the module level
embedding_service = EmbeddingService()

# Freeze the garbage collector to maximize COW memory sharing for worker processes
gc.freeze()
