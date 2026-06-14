# backend/models/embeddings.py
from sentence_transformers import SentenceTransformer
import numpy as np

MODEL_NAME = 'all-MiniLM-L6-v2'

# ---------------------------------------------------------
# 1.  Load model **once** at import  (fails fast if missing)
# ---------------------------------------------------------
print("Loading Sentence-BERT model …")
model = SentenceTransformer(MODEL_NAME)
print("Embedding model loaded:", MODEL_NAME)

# ---------------------------------------------------------
# 2.  Public helpers
# ---------------------------------------------------------
def generate_embedding(text: str) -> bytes:
    """
    Generate 384-dim vector for `text` and return it as
    a Python bytes blob ready for SQLite/BLOB storage.
    """
    embedding = model.encode(text, convert_to_tensor=True).cpu().numpy()
    return embedding.tobytes()          # float32 → bytes


def get_embedding_from_bytes(blob: bytes) -> np.ndarray:
    """
    Convert a bytes blob (from generate_embedding) back to
    a NumPy float32 array.
    """
    return np.frombuffer(blob, dtype=np.float32)