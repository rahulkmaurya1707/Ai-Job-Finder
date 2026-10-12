import re
from typing import List, Dict, Any, Tuple
from profile.user_profile import UserProfile

SENIOR_KEYWORDS = [
    "senior",
    "sr",
    "lead",
    "principal",
    "staff",
    "architect",
    "head",
    "director",
    "vp",
]
ENTRY_KEYWORDS = [
    "intern",
    "internship",
    "trainee",
    "fresher",
]


from config.indian_company_filter import (
    INDIAN_CITIES,
    INDIAN_STATES,
    INDIAN_COMPANIES,
    FOREIGN_LOCATION_KEYWORDS,
    FOREIGN_COMPANIES,
    is_indian_company_or_job,
)


def is_location_matched(
    job_location: str, preferred_locations: List[str], remote_ok: bool
) -> bool:
    """Check if job location matches user's location preferences or remote setting."""
    job_loc_lower = (job_location or "").lower()

    # Disallow foreign locations even under remote setting
    if any(fl in job_loc_lower for fl in FOREIGN_LOCATION_KEYWORDS) and "india" not in job_loc_lower:
        return False

    if remote_ok:
        return True

    if not preferred_locations:
        return True

    pref_lowers = [l.lower().strip() for l in preferred_locations if l and l.strip()]
    if "remote" in pref_lowers or not job_loc_lower:
        return True

    for loc in pref_lowers:
        if loc in job_loc_lower or job_loc_lower in loc:
            return True

    return True


def is_seniority_matched(job_title: str, experience_years: float) -> bool:
    """Filter out postings with seniority mismatch relative to candidate's experience."""
    title_lower = (job_title or "").lower()

    # Entry-level candidate (< 2 years exp): drop senior/lead/architect roles
    if experience_years < 2.0:
        for kw in SENIOR_KEYWORDS:
            if re.search(rf"\b{kw}\b", title_lower):
                return False

    # Senior candidate (> 5 years exp): drop pure intern/trainee roles
    if experience_years > 5.0:
        for kw in ENTRY_KEYWORDS:
            if re.search(rf"\b{kw}\b", title_lower):
                return False

    return True


def filter_job_postings(
    jobs: List[Dict[str, Any]], profile: UserProfile, indian_only: bool = False
) -> Tuple[List[Dict[str, Any]], int]:
    """Filter postings outside preferred locations (unless remote_ok), wrong seniority level, or non-Indian companies."""
    filtered_jobs = []
    dropped_count = 0

    for job in jobs:
        if not isinstance(job, dict):
            continue

        title = job.get("title", "")
        loc = job.get("location", "")

        # 1. Indian company filter if requested
        if indian_only and not is_indian_company_or_job(job):
            dropped_count += 1
            continue

        # 2. Location filter
        if not is_location_matched(loc, profile.locations if profile else [], profile.remote_ok if profile else True):
            dropped_count += 1
            continue

        # 3. Seniority & experience band filter
        if not is_seniority_matched(title, profile.experience_years if profile else 0.0):
            dropped_count += 1
            continue

        filtered_jobs.append(job)

    return filtered_jobs, dropped_count


