import re
from typing import List, Dict, Any, Tuple
from profile.user_profile import UserProfile

SENIOR_KEYWORDS = [
    "senior",
    "sr",
    "sr.",
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
    "junior",
    "jr",
    "entry level",
    "fresher",
]


def is_location_matched(
    job_location: str, preferred_locations: List[str], remote_ok: bool
) -> bool:
    """Check if job location matches user's location preferences or remote setting."""
    job_loc_lower = (job_location or "").lower()

    # Check if job is remote
    is_job_remote = "remote" in job_loc_lower or "anywhere" in job_loc_lower

    if remote_ok and is_job_remote:
        return True

    if not preferred_locations:
        return True

    # Check if job location matches any user location preference
    for loc in preferred_locations:
        loc_lower = loc.lower().strip()
        if loc_lower and (loc_lower in job_loc_lower or job_loc_lower in loc_lower):
            return True

    return False


def is_seniority_matched(job_title: str, experience_years: float) -> bool:
    """Filter out postings with mismatched seniority level relative to candidate's experience."""
    title_lower = (job_title or "").lower()

    # Entry-level candidate (< 2 years exp): drop senior/lead roles
    if experience_years < 2.0:
        for kw in SENIOR_KEYWORDS:
            if re.search(rf"\b{kw}\b", title_lower):
                return False

    # Senior candidate (> 5 years exp): drop intern/junior roles
    if experience_years > 5.0:
        for kw in ENTRY_KEYWORDS:
            if re.search(rf"\b{kw}\b", title_lower):
                return False

    return True


def filter_job_postings(
    jobs: List[Dict[str, Any]], profile: UserProfile
) -> Tuple[List[Dict[str, Any]], int]:
    """Filter postings outside preferred locations (unless remote_ok) or wrong seniority level."""
    filtered_jobs = []
    dropped_count = 0

    for job in jobs:
        if not isinstance(job, dict):
            continue

        title = job.get("title", "")
        loc = job.get("location", "")

        # 1. Location filter
        if not is_location_matched(loc, profile.locations, profile.remote_ok):
            dropped_count += 1
            continue

        # 2. Seniority & experience band filter
        if not is_seniority_matched(title, profile.experience_years):
            dropped_count += 1
            continue

        filtered_jobs.append(job)

    return filtered_jobs, dropped_count
