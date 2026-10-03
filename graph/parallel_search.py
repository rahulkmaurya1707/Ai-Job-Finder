import asyncio
from typing import List, Dict, Any
from storage.profile_storage import load_profile_from_json, load_profile_from_db
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
from graph.matcher import rank_jobs_by_resume_similarity

SEARCH_TOOLS = [
    ("RemoteOK", search_remoteok),
    ("WeWorkRemotely", search_weworkremotely),
    ("LinkedIn", search_linkedin),
    ("Indeed", search_indeed),
    ("Naukri", search_naukri),
]


async def fetch_jobs_from_tool_async(
    tool_name: str,
    tool_fn: Any,
    role: str,
    location: str,
    max_attempts: int = 2,
    delay_seconds: float = 1.0,
) -> List[Dict[str, str]]:
    """Asynchronously execute a search tool using asyncio thread pool with retry."""
    for attempt in range(1, max_attempts + 1):
        try:
            jobs = await asyncio.to_thread(tool_fn, query=role, location=location)
            if isinstance(jobs, list):
                valid_jobs = [j for j in jobs if isinstance(j, dict) and j.get("title")]
                if valid_jobs:
                    return valid_jobs
                if attempt < max_attempts:
                    await asyncio.sleep(delay_seconds)
                else:
                    return valid_jobs
            return []
        except Exception as e:
            if attempt < max_attempts:
                await asyncio.sleep(delay_seconds)
    return []


async def aggregate_all_jobs_parallel(
    roles: List[str] = None,
    locations: List[str] = None,
    profile: UserProfile = None,
    resume_text: str = "",
    top_k: int = 20,
) -> List[Dict[str, str]]:
    """Call MCP search tools in parallel, filter, deduplicate, and rank top-K by Chroma resume vector similarity."""
    user_prof = profile or load_profile_from_json()
    if not user_prof:
        user_prof = UserProfile(
            name="Default",
            preferred_roles=roles or ["Python Developer"],
            locations=locations or ["Remote"],
        )

    roles = roles or user_prof.preferred_roles or ["Python Developer"]
    locations = locations or user_prof.locations or ["Remote"]

    tasks = []
    for role in roles:
        for loc in locations:
            for tool_name, tool_fn in SEARCH_TOOLS:
                tasks.append(
                    fetch_jobs_from_tool_async(tool_name, tool_fn, role, loc)
                )

    results_nested = await asyncio.gather(*tasks, return_exceptions=True)

    raw_jobs = []
    for res in results_nested:
        if isinstance(res, list):
            raw_jobs.extend(res)

    # 1. Filter location & seniority
    filtered_jobs, _ = filter_job_postings(raw_jobs, user_prof)

    # 2. Deduplicate exact and fuzzy close matches
    deduped_jobs, _ = deduplicate_job_postings(filtered_jobs)

    # 3. Vector similarity ranking with Chroma and keep top-K
    top_k_jobs = rank_jobs_by_resume_similarity(
        resume_text=resume_text, jobs=deduped_jobs, top_k=top_k
    )

    return top_k_jobs


def run_parallel_job_search(
    roles: List[str] = None,
    locations: List[str] = None,
    profile: UserProfile = None,
    resume_text: str = "",
    top_k: int = 20,
) -> List[Dict[str, str]]:
    """Synchronous entry point to run parallel search, filtering, deduplication, and top-K vector ranking."""
    return asyncio.run(
        aggregate_all_jobs_parallel(roles, locations, profile, resume_text, top_k)
    )


from config import get_logger

logger = get_logger("parallel_search")

if __name__ == "__main__":
    jobs = run_parallel_job_search(
        roles=["Python"],
        locations=["Remote"],
        resume_text="Senior Python Engineer specialized in FastAPI, LangChain, and ChromaDB.",
        top_k=5,
    )
    logger.info(f"Top-{len(jobs)} Vector Ranked Jobs:")
    for j in jobs:
        logger.info(
            f"- Score: {j.get('similarity_score')} | [{j['source']}] {j['title']} @ {j['company']}"
        )
