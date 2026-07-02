"""
Singleton loader for the sentence-transformers embedding model.

Loading a transformer model from disk/HuggingFace Hub takes 1-3 seconds and a few
hundred MB of RAM. We load it exactly ONCE, when the FastAPI app starts (see the
`lifespan` function in main.py) - never inside a request handler. @lru_cache makes
every later call to get_embedding_model() return the same in-memory object instantly.
"""
from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.config import get_settings

settings = get_settings()


@lru_cache
def get_embedding_model() -> SentenceTransformer:
    """Returns a cached, process-wide instance of the embedding model."""
    return SentenceTransformer(
        settings.EMBEDDING_MODEL_NAME,
        cache_folder=settings.MODEL_CACHE_DIR,
    )