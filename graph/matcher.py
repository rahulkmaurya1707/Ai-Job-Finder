from typing import List, Dict, Any, Optional
import numpy as np
from rapidfuzz import fuzz

_embedding_fn: Optional[Any] = None


def get_embedding_fn():
    """Lazily load ONNXMiniLM_L6_V2 embedding function with error safety."""
    global _embedding_fn
    if _embedding_fn is None:
        try:
            from chromadb.utils import embedding_functions
            _embedding_fn = embedding_functions.ONNXMiniLM_L6_V2()
        except Exception:
            _embedding_fn = None
    return _embedding_fn


def _fallback_keyword_similarity(resume_text: str, job_text: str) -> float:
    """Fallback rapidfuzz token similarity when ONNX model is unavailable or in constrained cloud RAM."""
    if not resume_text or not job_text:
        return 0.5
    try:
        score = fuzz.token_set_ratio(resume_text, job_text) / 100.0
        return round(float(score), 4)
    except Exception:
        return 0.5


def rank_jobs_by_resume_similarity(
    resume_text: str,
    jobs: List[Dict[str, Any]],
    top_k: int = 20,
) -> List[Dict[str, Any]]:
    """Compute vector similarity between candidate resume vector and job description vectors using Chroma, with graceful keyword fallback."""
    if not jobs:
        return []

    if not resume_text:
        return jobs[:top_k]

    fn = get_embedding_fn()
    if fn is not None:
        try:
            # Generate vector embedding for candidate resume
            resume_embedding = fn([resume_text])[0]
            res_vec = np.array(resume_embedding, dtype=np.float32)
            res_norm = np.linalg.norm(res_vec)

            # Prepare job description text representations
            job_texts = [
                f"{j.get('title', '')} {j.get('company', '')} {j.get('description', '')}".strip()
                for j in jobs
            ]

            # Batch generate vector embeddings for all job descriptions
            job_embeddings = fn(job_texts)

            scored_jobs = []
            for idx, job in enumerate(jobs):
                job_vec = np.array(job_embeddings[idx], dtype=np.float32)
                job_norm = np.linalg.norm(job_vec)

                if res_norm > 0 and job_norm > 0:
                    cosine_sim = float(np.dot(res_vec, job_vec) / (res_norm * job_norm))
                else:
                    cosine_sim = 0.0

                job_copy = dict(job)
                job_copy["similarity_score"] = round(cosine_sim, 4)
                scored_jobs.append(job_copy)

            # Sort by vector similarity score in descending order
            scored_jobs.sort(key=lambda x: x["similarity_score"], reverse=True)
            return scored_jobs[:top_k]
        except Exception:
            pass

    # Resilient fallback if ONNX embedding is unavailable, slow, or fails on cloud container
    scored_jobs = []
    for job in jobs:
        job_text = f"{job.get('title', '')} {job.get('company', '')} {job.get('description', '')}".strip()
        sim = _fallback_keyword_similarity(resume_text, job_text)
        job_copy = dict(job)
        job_copy["similarity_score"] = sim
        scored_jobs.append(job_copy)

    scored_jobs.sort(key=lambda x: x["similarity_score"], reverse=True)
    return scored_jobs[:top_k]
