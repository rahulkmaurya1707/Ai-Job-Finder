from typing import List, Dict, Any
from rapidfuzz import fuzz


def calculate_similarity_score(resume_text: str, job: Dict[str, Any]) -> float:
    """Fast, memory-safe similarity calculation between resume and job description."""
    if not resume_text:
        return 0.5

    title = str(job.get("title", ""))
    company = str(job.get("company", ""))
    desc = str(job.get("description", ""))
    job_full = f"{title} {company} {desc}".strip()

    if not job_full:
        return 0.0

    # Token set ratio handles different word orders and partial matching
    ratio = fuzz.token_set_ratio(resume_text.lower(), job_full.lower()) / 100.0

    # Boost score if key title words appear in candidate skills/resume
    title_words = [w for w in title.lower().split() if len(w) > 3]
    if title_words and any(w in resume_text.lower() for w in title_words):
        ratio = min(1.0, ratio + 0.15)

    return round(float(ratio), 4)


def rank_jobs_by_resume_similarity(
    resume_text: str,
    jobs: List[Dict[str, Any]],
    top_k: int = 20,
) -> List[Dict[str, Any]]:
    """Compute high-accuracy similarity score without heavy ONNX models to prevent 512MB RAM OOM crashes on Render."""
    if not jobs:
        return []

    if not resume_text:
        return jobs[:top_k]

    scored_jobs = []
    for job in jobs:
        sim = calculate_similarity_score(resume_text, job)
        job_copy = dict(job)
        job_copy["similarity_score"] = sim
        scored_jobs.append(job_copy)

    # Sort from highest to lowest similarity
    scored_jobs.sort(key=lambda x: x["similarity_score"], reverse=True)
    return scored_jobs[:top_k]
