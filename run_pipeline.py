from graph.workflow import app_graph
from storage.profile_storage import load_profile_from_json
from storage.vector_store import store_resume_vector
from mcp_servers.health import ping_mcp_tools
from config import setup_logging, get_logger

# Initialize central logging with RotatingFileHandler
setup_logging()
logger = get_logger("run_pipeline")


def main():
    logger.info("==================================================")
    logger.info("Running Job Finder LangGraph Pipeline End-to-End")
    logger.info("==================================================")

    # Ping each MCP tool briefly before a full run and log any that are unreachable
    ping_mcp_tools()

    profile = load_profile_from_json()
    if not profile:
        profile = UserProfile(
            name="Candidate",
            skills=["Python", "JavaScript", "React", "Node.js", "SQL", "Git"],
            preferred_roles=["Software Engineer", "Full-Stack Developer", "Frontend Developer"],
            experience_years=0.0,
            remote_ok=True,
        )
        save_profile_to_json(profile)
        save_profile_to_db(profile)

    logger.info(f"Loaded Profile for: {profile.name}")
    logger.info(f"Preferred Roles: {profile.preferred_roles}")
    logger.info(f"Skills: {profile.skills}")

    # Seed vector store with profile summary
    resume_summary = (
        f"{profile.name} - Senior Software & AI Engineer. "
        f"Expertise in {', '.join(profile.skills)}. {profile.experience_years} years experience."
    )
    store_resume_vector(user_name=profile.name, resume_text=resume_summary)

    initial_state = {
        "profile": profile,
        "resume_summary": resume_summary,
    }

    logger.info("Executing LangGraph StateGraph (7 Nodes)...")
    final_state = app_graph.invoke(initial_state)

    shortlist = final_state.get("shortlist", [])
    run_id = final_state.get("run_id", "N/A")

    logger.info("=" * 100)
    logger.info(f"FINAL JOB SHORTLIST TABLE (Run ID: {run_id})")
    logger.info("=" * 100)

    header = f"| {'#':<2} | {'Job Title':<38} | {'Company':<20} | {'Location':<15} | {'Match %':<7} | {'Recommendation':<14} |"
    divider = "+" + "-" * (len(header) - 2) + "+"
    logger.info(divider)
    logger.info(header)
    logger.info(divider)

    for idx, job in enumerate(shortlist, start=1):
        eval_data = job.get("evaluation", {})
        score = eval_data.get("match_score", "N/A")
        rec = str(eval_data.get("recommendation", "N/A")).replace("RecommendationEnum.", "")
        reasoning = eval_data.get("one_line_reasoning", "")
        matching_skills = eval_data.get("matching_skills", [])
        missing_skills = eval_data.get("missing_skills", [])
        title = (job.get("title", "N/A")[:36] + "..") if len(job.get("title", "N/A")) > 38 else job.get("title", "N/A")
        company = (job.get("company", "N/A")[:18] + "..") if len(job.get("company", "N/A")) > 20 else job.get("company", "N/A")
        loc = (job.get("location", "N/A")[:13] + "..") if len(job.get("location", "N/A")) > 15 else job.get("location", "N/A")
        url = job.get("apply_url", "#")

        row = f"| {idx:<2} | {title:<38} | {company:<20} | {loc:<15} | {str(score)+'%':<7} | {rec:<14} |"
        logger.info(row)
        logger.info(f"  +--> Reasoning: {reasoning}")
        logger.info(f"       Matching:  {', '.join(matching_skills) if matching_skills else 'None'}")
        logger.info(f"       Missing:   {', '.join(missing_skills) if missing_skills else 'None'}")
        logger.info(f"       Apply URL: {url}")
        logger.info(divider)

    logger.info("[OK] Pipeline execution finished successfully.")


if __name__ == "__main__":
    main()
