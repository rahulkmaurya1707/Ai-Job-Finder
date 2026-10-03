import hashlib
import re
from typing import List, Dict, Any, Tuple
from rapidfuzz import fuzz


def normalize_text(text: str) -> str:
    """Lowercase, strip punctuation, and collapse multiple whitespaces."""
    if not text:
        return ""
    cleaned = re.sub(r"[^\w\s]", "", str(text).lower())
    return " ".join(cleaned.split())


def generate_posting_hash(job: Dict[str, Any]) -> str:
    """Create SHA256 hash key from normalized (title + company + location)."""
    norm_title = normalize_text(job.get("title", ""))
    norm_company = normalize_text(job.get("company", ""))
    norm_location = normalize_text(job.get("location", ""))

    raw_key = f"{norm_title}|{norm_company}|{norm_location}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def is_fuzzy_match(
    job1: Dict[str, Any], job2: Dict[str, Any], threshold: float = 70.0
) -> bool:
    """Use rapidfuzz token_set_ratio to detect near-identical job titles and companies."""
    title1 = normalize_text(job1.get("title", ""))
    title2 = normalize_text(job2.get("title", ""))
    comp1 = normalize_text(job1.get("company", ""))
    comp2 = normalize_text(job2.get("company", ""))

    title_sim = fuzz.token_set_ratio(title1, title2)
    company_sim = (
        fuzz.token_set_ratio(comp1, comp2)
        if (comp1 and comp2)
        else 100.0
    )

    return title_sim >= threshold and company_sim >= threshold


def deduplicate_job_postings(
    jobs: List[Dict[str, Any]], fuzzy_threshold: float = 70.0
) -> Tuple[List[Dict[str, Any]], int]:
    """Drop postings with repeated hash keys or rapidfuzz close matches."""
    seen_hashes = set()
    deduped_jobs = []
    dropped_count = 0

    for job in jobs:
        if not isinstance(job, dict):
            continue

        h_key = generate_posting_hash(job)
        if h_key in seen_hashes:
            dropped_count += 1
            continue

        is_fuzzy_dup = False
        for existing_job in deduped_jobs:
            if is_fuzzy_match(job, existing_job, threshold=fuzzy_threshold):
                is_fuzzy_dup = True
                dropped_count += 1
                break

        if not is_fuzzy_dup:
            seen_hashes.add(h_key)
            job_copy = dict(job)
            job_copy["hash_key"] = h_key
            deduped_jobs.append(job_copy)

    return deduped_jobs, dropped_count
