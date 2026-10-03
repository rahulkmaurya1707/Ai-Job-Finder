from typing import List, Dict, Any
import numpy as np
from chromadb.utils import embedding_functions

embedding_fn = embedding_functions.ONNXMiniLM_L6_V2()


def rank_jobs_by_resume_similarity(
    resume_text: str,
    jobs: List[Dict[str, Any]],
    top_k: int = 20,
) -> List[Dict[str, Any]]:
    """Compute vector similarity between candidate resume vector and job description vectors using Chroma, keeping top-K most similar jobs."""
    if not jobs:
        return []

    if not resume_text:
        return jobs[:top_k]

    # Generate vector embedding for candidate resume
    resume_embedding = embedding_fn([resume_text])[0]
    res_vec = np.array(resume_embedding, dtype=np.float32)
    res_norm = np.linalg.norm(res_vec)

    # Prepare job description text representations
    job_texts = [
        f"{j.get('title', '')} {j.get('company', '')} {j.get('description', '')}".strip()
        for j in jobs
    ]

    # Batch generate vector embeddings for all job descriptions
    job_embeddings = embedding_fn(job_texts)

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

    # Keep top-K most similar jobs
    return scored_jobs[:top_k]
