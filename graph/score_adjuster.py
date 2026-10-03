import re
from typing import Dict, Any, Optional
from profile.user_profile import UserProfile


def adjust_match_score(
    base_score: int, job: Dict[str, Any], profile: Optional[UserProfile]
) -> int:
    """Slightly boost match score for exact location or salary match (+5), and slightly reduce for partial mismatch (-5)."""
    score = float(base_score)
    if not profile:
        return max(0, min(100, int(round(score))))

    job_loc = (job.get("location") or "").lower().strip()
    job_desc = (job.get("description") or "").lower()

    # 1. Location match boost / partial mismatch penalty
    if profile.locations:
        exact_location_match = any(
            loc.lower().strip() == job_loc for loc in profile.locations if loc
        )
        if exact_location_match:
            score += 5.0  # Boost for exact location match
        elif not ("remote" in job_loc and profile.remote_ok):
            # Partial location mismatch check
            partial_match = any(
                loc.lower().strip() in job_loc for loc in profile.locations if loc
            )
            if not partial_match:
                score -= 5.0  # Penalty for partial location mismatch

    # 2. Salary match boost / partial mismatch penalty
    if profile.min_salary and profile.min_salary > 0:
        salaries = [
            float(s.replace(",", ""))
            for s in re.findall(r"\$?\b(\d{2,3}(?:,\d{3})+|\d{5,6})\b", job_desc)
        ]
        if salaries:
            max_offered = max(salaries)
            if max_offered >= profile.min_salary:
                score += 5.0  # Boost for meeting salary expectation
            else:
                score -= 5.0  # Penalty for below salary expectation

    return max(0, min(100, int(round(score))))
