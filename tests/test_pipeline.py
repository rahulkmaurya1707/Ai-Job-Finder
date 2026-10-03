import pytest
from profile.user_profile import UserProfile
from graph.deduplicator import deduplicate_job_postings
from graph.filters import filter_job_postings
from graph.nodes import rank_node
from graph.state import GraphState

# --- Fixed Sample Test Data ---

SAMPLE_RAW_POSTINGS = [
    {
        "title": "Software Engineer",
        "company": "Prenosis",
        "location": "Remote",
        "source": "RemoteOK",
        "apply_url": "https://remoteok.com/1",
    },
    {
        "title": "Software Engineer",
        "company": "Prenosis",
        "location": "Remote",
        "source": "WeWorkRemotely",
        "apply_url": "https://remoteok.com/1",
    },  # Exact Duplicate Hash
    {
        "title": "Software Engineer (Python)",
        "company": "Prenosis Inc",
        "location": "Remote",
        "source": "LinkedIn",
        "apply_url": "https://linkedin.com/1",
    },  # Fuzzy Duplicate
    {
        "title": "Backend Software Engineer",
        "company": "Airspace Link",
        "location": "Remote",
        "source": "RemoteOK",
        "apply_url": "https://remoteok.com/2",
    },
    {
        "title": "Senior Lead Architect",
        "company": "Big Corp",
        "location": "New York, NY",
        "source": "LinkedIn",
        "apply_url": "https://linkedin.com/2",
    },  # Senior Role / Non-remote
    {
        "title": "Junior Python Intern",
        "company": "Startup Co",
        "location": "Remote",
        "source": "RemoteOK",
        "apply_url": "https://remoteok.com/3",
    },  # Intern Role
]


# --- Unit Tests ---

def test_deduplication():
    """Test exact hash and rapidfuzz fuzzy deduplication logic with fixed sample data."""
    deduped, dropped_count = deduplicate_job_postings(
        SAMPLE_RAW_POSTINGS, fuzzy_threshold=70.0
    )

    # From 6 raw postings, 2 are duplicate postings of Prenosis Software Engineer
    assert dropped_count >= 2
    assert len(deduped) == len(SAMPLE_RAW_POSTINGS) - dropped_count

    titles = [j["title"] for j in deduped]
    assert "Backend Software Engineer" in titles
    assert "Senior Lead Architect" in titles


def test_filtering_location_and_seniority():
    """Test location preference and seniority level filtering with fixed sample data."""
    # Entry-level candidate (1 year exp, Remote OK)
    entry_profile = UserProfile(
        name="Alice Entry",
        skills=["Python", "FastAPI"],
        experience_years=1.0,
        locations=["Remote"],
        remote_ok=True,
    )

    filtered_jobs, dropped = filter_job_postings(SAMPLE_RAW_POSTINGS, entry_profile)

    # Senior Lead Architect should be dropped for entry-level candidate
    filtered_titles = [j["title"] for j in filtered_jobs]
    assert "Senior Lead Architect" not in filtered_titles
    assert "Software Engineer" in filtered_titles
    assert dropped > 0


def test_senior_candidate_filtering():
    """Test senior candidate filtering out intern/junior roles."""
    senior_profile = UserProfile(
        name="Bob Senior",
        skills=["Python", "System Architecture"],
        experience_years=8.0,
        locations=["Remote"],
        remote_ok=True,
    )

    filtered_jobs, dropped = filter_job_postings(SAMPLE_RAW_POSTINGS, senior_profile)

    # Junior Python Intern should be dropped for senior candidate (8+ yrs exp)
    filtered_titles = [j["title"] for j in filtered_jobs]
    assert "Junior Python Intern" not in filtered_titles


def test_score_thresholding_and_ranking():
    """Test score-thresholding cutoff filter and top N ranking in rank_node."""
    scored_sample = [
        {
            "title": "High Match Job 1",
            "company": "Tech A",
            "location": "Remote",
            "evaluation": {"match_score": 95, "recommendation": "Apply"},
        },
        {
            "title": "High Match Job 2",
            "company": "Tech B",
            "location": "Remote",
            "evaluation": {"match_score": 85, "recommendation": "Apply"},
        },
        {
            "title": "Borderline Match Job",
            "company": "Tech C",
            "location": "Remote",
            "evaluation": {"match_score": 60, "recommendation": "Consider"},
        },
        {
            "title": "Low Match Job (Below Cutoff)",
            "company": "Tech D",
            "location": "Remote",
            "evaluation": {"match_score": 45, "recommendation": "Skip"},
        },
    ]

    state: GraphState = {
        "scored_postings": scored_sample,
        "resume_summary": "Python Developer with 4 years exp",
    }

    result = rank_node(state)
    shortlist = result["shortlist"]

    # Low Match Job (45%) should be filtered out because cutoff is 60%
    shortlist_titles = [j["title"] for j in shortlist]
    assert "Low Match Job (Below Cutoff)" not in shortlist_titles
    assert "High Match Job 1" in shortlist_titles

    # Verify scores are sorted in descending order
    scores = [j["evaluation"]["match_score"] for j in shortlist]
    assert scores == sorted(scores, reverse=True)


def test_mcp_tools_ping_health_check():
    """Test pinging each MCP tool briefly before a run and checking reachability status."""
    from mcp_servers.health import ping_mcp_tools

    results = ping_mcp_tools(timeout_per_tool=5.0)

    expected_tools = {
        "search_linkedin",
        "search_naukri",
        "search_indeed",
        "search_remoteok",
        "search_weworkremotely",
        "get_profile_resume_embedding",
        "send_notification_tool",
    }

    assert expected_tools.issubset(set(results.keys()))

    for tool_name in expected_tools:
        info = results[tool_name]
        assert "reachable" in info
        assert "reason" in info
        assert isinstance(info["reachable"], bool)


def test_resume_parser_docx_and_pdf():
    """Test extracting raw resume text from DOCX using python-docx and pdfplumber parser routing."""
    import io
    import docx
    from profile.resume_parser import extract_text_from_resume, extract_text_from_docx

    # Create synthetic DOCX file stream
    doc = docx.Document()
    doc.add_heading("Jane Doe - AI Engineer", 0)
    doc.add_paragraph("Specialized in Python, FastAPI, and LangChain.")
    docx_stream = io.BytesIO()
    doc.save(docx_stream)

    extracted_text = extract_text_from_resume(docx_stream.getvalue(), "resume.docx")
    assert "Jane Doe - AI Engineer" in extracted_text
    assert "FastAPI" in extracted_text


