import asyncio
import logging
from typing import Dict, Any, List
from graph.state import GraphState
from storage.profile_storage import load_profile_from_json
from storage.job_storage import save_shortlist_to_db
from profile.user_profile import UserProfile
from mcp_servers.server import (
    search_linkedin,
    search_naukri,
    search_indeed,
    search_remoteok,
    search_weworkremotely,
)
from graph.deduplicator import deduplicate_job_postings
from graph.filters import filter_job_postings
from graph.job_evaluator import evaluate_job_match
from graph.score_adjuster import adjust_match_score
from graph.matcher import rank_jobs_by_resume_similarity
from config import settings, get_logger
from mcp_servers.notification_tool import send_notification
from graph.cover_letter_generator import generate_cover_letter_draft

logger = get_logger(__name__)

SEARCH_TOOLS = [
    ("RemoteOK", search_remoteok),
    ("WeWorkRemotely", search_weworkremotely),
    ("LinkedIn", search_linkedin),
    ("Indeed", search_indeed),
    ("Naukri", search_naukri),
]


def load_profile_node(state: GraphState) -> Dict[str, Any]:
    """Node 1: Load UserProfile and resume summary into graph state."""
    profile = (
        state.get("profile")
        if state.get("profile") is not None
        else load_profile_from_json()
    )
    if not profile:
        profile = UserProfile(
            name="Default Candidate",
            preferred_roles=["Python Developer"],
            locations=["Remote"],
        )
    resume_summary = (
        state.get("resume_summary")
        or f"{profile.name} - Skills: {', '.join(profile.skills)}"
    )
    return {"profile": profile, "resume_summary": resume_summary}


async def _fetch_jobs_async(
    tool_name: str,
    tool_fn: Any,
    role: str,
    loc: str,
    timeout_seconds: float = 12.0,
    max_attempts: int = 2,
    delay_seconds: float = 1.0,
) -> List[Dict[str, Any]]:
    """Fetch jobs from an MCP tool asynchronously with retry (up to max_attempts) & error logging."""
    for attempt in range(1, max_attempts + 1):
        try:
            res = await asyncio.wait_for(
                asyncio.to_thread(tool_fn, query=role, location=loc),
                timeout=timeout_seconds,
            )
            if isinstance(res, list):
                valid_jobs = []
                for j in res:
                    if isinstance(j, dict):
                        if j.get("error"):
                            logger.warning(
                                f"Source '{tool_name}' reported error on attempt {attempt}/{max_attempts}: {j['error']}"
                            )
                        elif j.get("title"):
                            valid_jobs.append(j)
                if valid_jobs:
                    return valid_jobs
                # If source returned empty/error on attempt < max_attempts, retry after short delay
                if attempt < max_attempts:
                    logger.info(
                        f"Source '{tool_name}' returned 0 valid jobs on attempt {attempt}/{max_attempts}. Retrying in {delay_seconds}s..."
                    )
                    await asyncio.sleep(delay_seconds)
                else:
                    return valid_jobs
            return []
        except asyncio.TimeoutError:
            logger.warning(
                f"Source '{tool_name}' timed out after {timeout_seconds}s on attempt {attempt}/{max_attempts} for query '{role}'."
            )
            if attempt < max_attempts:
                await asyncio.sleep(delay_seconds)
        except Exception as e:
            logger.warning(
                f"Source '{tool_name}' failed with error on attempt {attempt}/{max_attempts}: {str(e)}."
            )
            if attempt < max_attempts:
                await asyncio.sleep(delay_seconds)

    logger.warning(
        f"Source '{tool_name}' failed after {max_attempts} attempts. Marking as failed for this run."
    )
    return []


def search_sources_node(state: GraphState) -> Dict[str, Any]:
    """Node 2: Call all MCP search tools in parallel using asyncio."""
    if state.get("raw_postings"):
        return {"raw_postings": state.get("raw_postings")}

    profile = state.get("profile")
    roles = (
        profile.preferred_roles
        if profile and profile.preferred_roles
        else ["Python Developer"]
    )
    locations = (
        profile.locations if profile and profile.locations else ["Remote"]
    )

    enabled_sources = settings.JOB_SOURCES
    active_tools = [
        (name, fn) for name, fn in SEARCH_TOOLS if name in enabled_sources
    ]

    async def _run_all_searches():
        tasks = []
        for r in roles:
            for l in locations:
                for name, fn in active_tools:
                    tasks.append(_fetch_jobs_async(name, fn, r, l))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        raw = []
        for item in results:
            if isinstance(item, list):
                raw.extend(item)
            elif isinstance(item, Exception):
                logger.warning(
                    f"A job search task failed with exception: {item}. Continuing."
                )
        return raw

    raw_postings = asyncio.run(_run_all_searches())
    counts_by_source = {}
    for j in raw_postings:
        src = j.get("source", "Unknown")
        counts_by_source[src] = counts_by_source.get(src, 0) + 1

    logger.info(
        f"[METRICS] Raw postings found per source: {counts_by_source} (Total: {len(raw_postings)})"
    )
    return {"raw_postings": raw_postings}


def dedupe_node(state: GraphState) -> Dict[str, Any]:
    """Node 3: Apply exact hash and rapidfuzz fuzzy deduplication."""
    raw_postings = state.get("raw_postings") or []
    deduped_postings, removed_dups = deduplicate_job_postings(raw_postings)
    logger.info(
        f"[METRICS] Duplicate postings removed: {removed_dups} (Remaining deduped: {len(deduped_postings)})"
    )
    return {"deduped_postings": deduped_postings}


def filter_node(state: GraphState) -> Dict[str, Any]:
    """Node 4: Filter out postings by location preference and seniority level."""
    deduped_postings = state.get("deduped_postings") or []
    profile = state.get("profile")
    filtered_postings, dropped_filters = filter_job_postings(deduped_postings, profile)
    logger.info(
        f"[METRICS] Postings passed filters: {len(filtered_postings)} (Filtered out: {dropped_filters})"
    )
    return {"filtered_postings": filtered_postings}


def widen_criteria_node(state: GraphState) -> Dict[str, Any]:
    """Widens location/experience criteria once when zero jobs survive filter."""
    logger.info(
        "Zero jobs survived initial filter. Widening location and experience criteria once."
    )
    profile = state.get("profile")
    if profile:
        profile.remote_ok = True
        if "Remote" not in profile.locations:
            profile.locations.append("Remote")
        profile.experience_years = 3.0  # Mid-level flexible range

    return {"profile": profile, "widened_criteria": True}


def route_after_filter(state: GraphState) -> str:
    """Conditional router: if zero jobs survive filter and hasn't widened yet, route to widen_criteria."""
    filtered_postings = state.get("filtered_postings") or []
    widened_criteria = state.get("widened_criteria", False)

    if len(filtered_postings) == 0 and not widened_criteria:
        return "widen_criteria"
    return "match_score"


def match_score_node(state: GraphState) -> Dict[str, Any]:
    """Node 5: Evaluate filtered jobs with Groq/LangChain and apply match score adjustments."""
    filtered_postings = state.get("filtered_postings") or []
    resume_summary = state.get("resume_summary") or "Candidate Resume"
    profile = state.get("profile")

    scored_postings = []
    for job in filtered_postings:
        job_desc = (
            f"Title: {job.get('title', '')}\n"
            f"Company: {job.get('company', '')}\n"
            f"Location: {job.get('location', '')}\n"
            f"Description: {job.get('description', '')}"
        )
        try:
            eval_res = evaluate_job_match(
                resume_summary=resume_summary, job_description=job_desc
            )
            eval_dict = eval_res.model_dump()
            raw_score = eval_dict.get("match_score", 50)
            adjusted_score = adjust_match_score(
                base_score=raw_score, job=job, profile=profile
            )
            eval_dict["match_score"] = adjusted_score
            eval_dict["raw_score"] = raw_score

            rec_val = str(eval_dict.get("recommendation", "")).replace(
                "RecommendationEnum.", ""
            )
            cover_letter = ""
            if rec_val.lower() == "apply":
                logger.info(
                    f"Job '{job.get('title')}' recommended for APPLY. Generating cover letter draft via Groq..."
                )
                cover_letter = generate_cover_letter_draft(
                    resume_summary=resume_summary,
                    job_title=job.get("title", ""),
                    company_name=job.get("company", ""),
                    job_description=job_desc,
                )

            eval_dict["cover_letter_draft"] = cover_letter
            job_copy = dict(job)
            job_copy["evaluation"] = eval_dict
            job_copy["cover_letter_draft"] = cover_letter
            scored_postings.append(job_copy)
        except Exception as e:
            logger.warning(f"Evaluation error for job '{job.get('title')}': {e}")
            job_copy = dict(job)
            job_copy["evaluation"] = {
                "match_score": 50,
                "raw_score": 50,
                "matching_skills": [],
                "missing_skills": [],
                "recommendation": "Consider",
                "one_line_reasoning": f"Evaluation error: {str(e)}",
            }
            scored_postings.append(job_copy)

    return {"scored_postings": scored_postings}


def rank_node(state: GraphState) -> Dict[str, Any]:
    """Node 6: Rank scored jobs by vector similarity, cutoff filter, and slice top N into shortlist."""
    scored_postings = state.get("scored_postings") or []
    resume_summary = state.get("resume_summary") or ""
    cutoff = settings.MATCH_SCORE_CUTOFF
    top_n = settings.FINAL_TOP_N_JOBS

    # Filter out jobs below cutoff
    passing_jobs = [
        j
        for j in scored_postings
        if j.get("evaluation", {}).get("match_score", 0) >= cutoff
    ]

    # Rank by vector similarity if resume summary exists
    ranked_jobs = rank_jobs_by_resume_similarity(
        resume_text=resume_summary, jobs=passing_jobs, top_k=len(passing_jobs)
    )

    # Sort from highest to lowest match_score
    ranked_jobs.sort(
        key=lambda j: j.get("evaluation", {}).get("match_score", 0), reverse=True
    )

    shortlist = ranked_jobs[:top_n]
    return {"shortlist": shortlist}


def present_node(state: GraphState) -> Dict[str, Any]:
    """Node 7: Present final shortlist, save to SQLite with run_id and timestamp."""
    shortlist = state.get("shortlist") or []
    profile = state.get("profile")
    user_name = profile.name if profile else "User"

    run_id = save_shortlist_to_db(
        shortlist_jobs=shortlist, user_name=user_name, run_id=state.get("run_id")
    )

    for j in shortlist:
        j["run_id"] = run_id

    logger.info(
        f"[METRICS] Final shortlist size: {len(shortlist)} jobs saved to SQLite (run_id: {run_id})."
    )
    print(
        f"[METRICS] Final shortlist size: {len(shortlist)} jobs saved to SQLite (run_id: {run_id})."
    )

    return {"shortlist": shortlist, "run_id": run_id}


def notify_node(state: GraphState) -> Dict[str, Any]:
    """Node 8: Send clean card-style Telegram notification with emojis."""
    shortlist = state.get("shortlist") or []
    threshold = settings.MATCH_SCORE_CUTOFF

    # Filter jobs meeting or exceeding the match score threshold
    qualifying_jobs = [
        j
        for j in shortlist
        if j.get("evaluation", {}).get("match_score", 0) >= threshold
    ]

    number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

    if len(qualifying_jobs) > 0:
        msg_lines = [
            f"Found {len(qualifying_jobs)} matching job(s):\n"
        ]
        for idx, job in enumerate(qualifying_jobs, start=1):
            eval_data = job.get("evaluation", {})
            score = eval_data.get("match_score", 0)
            rec = (
                str(eval_data.get("recommendation", "Consider"))
                .replace("RecommendationEnum.", "")
                .strip()
                .capitalize()
            )
            title = job.get("title", "N/A")
            company = job.get("company", "N/A")
            location = job.get("location", "N/A")
            apply_url = job.get("apply_url", "#")

            num_str = number_emojis[idx - 1] if idx <= len(number_emojis) else f"{idx}."

            msg_lines.append(f"{num_str} {title}")
            msg_lines.append(f"🏢 Company: {company}")
            msg_lines.append(f"📍 Location: {location}")
            msg_lines.append(f"🔥 Match: {score}%")
            msg_lines.append(f"💡 Recommendation: {rec}")
            msg_lines.append(f"🔗 Apply: {apply_url}")
            msg_lines.append("")

        notification_text = "\n".join(msg_lines).strip()
        notif_result = send_notification(
            message=notification_text,
            subject="🤖 AI Job Finder",
        )
        logger.info(f"[NODE notify] Notification dispatched: {notif_result}")
    else:
        logger.info(
            f"[NODE notify] Zero jobs scored above threshold ({threshold}%). Staying silent."
        )

    return {}
