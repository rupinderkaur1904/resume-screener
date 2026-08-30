"""
Unit tests for the match-scoring math in app/ml/inference.py.
These don't load the actual sentence-transformers model - they test the
scoring math directly with fixed vectors, which is the whole point of
keeping these as pure functions.
"""
from app.ml.inference import compute_match_score, compute_match_scores_batch


def test_identical_vectors_score_high():
    vec = [1.0, 0.0, 0.0]
    score = compute_match_score(vec, vec)
    assert score == 100.0


def test_orthogonal_vectors_score_at_or_near_zero():
    vec_a = [1.0, 0.0]
    vec_b = [0.0, 1.0]
    score = compute_match_score(vec_a, vec_b)
    assert score == 0.0


def test_score_is_clamped_between_0_and_100():
    vec = [1.0, 0.0]
    score = compute_match_score(vec, vec)
    assert 0.0 <= score <= 100.0


def test_batch_scoring_matches_individual_scoring():
    resume = [1.0, 0.0, 0.0]
    jobs = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.7, 0.7, 0.0]]

    batch_scores = compute_match_scores_batch(resume, jobs)
    individual_scores = [compute_match_score(resume, job) for job in jobs]

    assert batch_scores == individual_scores


def test_batch_scoring_preserves_order():
    resume = [1.0, 0.0]
    jobs = [[1.0, 0.0], [0.0, 1.0]]

    scores = compute_match_scores_batch(resume, jobs)
    assert scores[0] > scores[1]
