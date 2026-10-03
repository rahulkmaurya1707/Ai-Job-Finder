from typing import List, Dict, Any, Optional
from graph.job_evaluator import evaluate_job_match
from graph.score_adjuster import adjust_match_score
from storage.job_storage import save_evaluated_jobs, save_shortlist_to_db
from profile.user_profile import UserProfile
from config import settings


def process_and_evaluate_top_jobs(
    top_jobs: List[Dict[str, Any]],
    resume_summary: str,
    min_score_cutoff: Optional[int] = None,
    profile: Optional[UserProfile] = None,
    top_n: Optional[int] = None,
    run_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Call Groq via LangChain for top jobs, apply score adjustments, filter below cutoff, sort, and store final shortlist in SQLite with run_id and timestamp."""
    cutoff = (
        min_score_cutoff
        if min_score_cutoff is not None
        else settings.MATCH_SCORE_CUTOFF
    )
    limit_n = top_n if top_n is not None else settings.FINAL_TOP_N_JOBS
    evaluated_jobs = []

    for job in top_jobs:
        job_desc = (
            f"Title: {job.get('title', '')}\n"
            f"Company: {job.get('company', '')}\n"
            f"Location: {job.get('location', '')}\n"
            f"Description: {job.get('description', '')}"
        )

        try:
            eval_result = evaluate_job_match(
                resume_summary=resume_summary, job_description=job_desc
            )
            eval_dict = eval_result.model_dump()
            raw_score = eval_dict.get("match_score", 50)

            # Apply location and salary score boost/penalty adjustment
            adjusted_score = adjust_match_score(
                base_score=raw_score, job=job, profile=profile
            )
            eval_dict["match_score"] = adjusted_score
            eval_dict["raw_score"] = raw_score

            job_copy = dict(job)
            job_copy["evaluation"] = eval_dict
            evaluated_jobs.append(job_copy)
        except Exception as e:
            job_copy = dict(job)
            job_copy["evaluation"] = {
                "match_score": 50,
                "raw_score": 50,
                "matching_skills": [],
                "missing_skills": [],
                "recommendation": "Consider",
                "one_line_reasoning": f"Evaluation error: {str(e)}",
            }
            evaluated_jobs.append(job_copy)

    # Filter out jobs with match_score below configurable cutoff
    passing_jobs = [
        j
        for j in evaluated_jobs
        if (
            j.get("evaluation", {}).get("match_score", 0)
            if isinstance(j.get("evaluation"), dict)
            else getattr(j.get("evaluation"), "match_score", 0)
        )
        >= cutoff
    ]

    # Order passing jobs from highest to lowest match_score
    passing_jobs.sort(
        key=lambda j: j.get("evaluation", {}).get("match_score", 0)
        if isinstance(j.get("evaluation"), dict)
        else getattr(j.get("evaluation"), "match_score", 0),
        reverse=True,
    )

    # Keep only top N jobs in the final shortlist
    final_shortlist = passing_jobs[:limit_n]

    # Save evaluated jobs and final shortlist into SQLite database
    save_evaluated_jobs(final_shortlist)
    user_name = profile.name if profile else "User"
    saved_run_id = save_shortlist_to_db(
        shortlist_jobs=final_shortlist, run_id=run_id, user_name=user_name
    )

    for j in final_shortlist:
        j["run_id"] = saved_run_id

    return final_shortlist
