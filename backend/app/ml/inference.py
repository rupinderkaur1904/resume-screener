"""
Turn text into embeddings, and turn two embeddings into a 0-100 match score.
Kept as plain functions (not a class) so they're easy to unit test with
fixed input vectors.
"""
from typing import List

import numpy as np
from sentence_transformers import util

from app.ml.model_loader import get_embedding_model

# Raw cosine similarity for real resume/job pairs tends to cluster between
# 0.20 and 0.70 rather than spanning the full 0-1 range, so we rescale that
# window to 0-100 to get scores that feel intuitive to a user.
RAW_SCORE_MIN = 0.20
RAW_SCORE_MAX = 0.70


def embed_text(text: str) -> List[float]:
    """Convert raw text (resume body or job description) into a dense vector."""
    model = get_embedding_model()
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


def _rescale(raw_similarity: float) -> float:
    """Map a raw cosine similarity into a 0-100 score, clamped at both ends."""
    score = (raw_similarity - RAW_SCORE_MIN) / (RAW_SCORE_MAX - RAW_SCORE_MIN) * 100
    return round(max(0.0, min(100.0, score)), 2)


def compute_match_score(resume_embedding: List[float], job_embedding: List[float]) -> float:
    """Cosine similarity between two normalized embeddings, rescaled to 0-100."""
    sim = util.cos_sim(np.array(resume_embedding), np.array(job_embedding)).item()
    sim = max(0.0, min(1.0, sim))
    return _rescale(sim)


def compute_match_scores_batch(
    resume_embedding: List[float], job_embeddings: List[List[float]]
) -> List[float]:
    """
    Score one resume against many jobs in a single vectorized call.
    Returns scores in the same order as job_embeddings was passed in.
    """
    resume_vec = np.array(resume_embedding)
    job_matrix = np.array(job_embeddings)

    sims = util.cos_sim(resume_vec, job_matrix)[0]
    sims = sims.clamp(0.0, 1.0)

    return [_rescale(s.item()) for s in sims]
