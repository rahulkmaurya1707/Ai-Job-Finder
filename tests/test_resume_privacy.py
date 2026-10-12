import json
from pathlib import Path
from profile.user_profile import UserProfile
from storage.profile_storage import (
    load_profile_from_json,
    save_profile_to_json,
    clear_profile_from_json,
    clear_all_profiles_from_db,
    init_db,
    save_profile_to_db,
    DB_FILE,
    JSON_FILE,
)
from storage.vector_store import (
    get_vector_store,
    store_resume_vector,
    delete_resume_vector,
    clear_all_resume_vectors,
)


def test_user_profile_json_is_not_saving_last_person_resume():
    """Verify user_profile.json contains no residual personal resume data."""
    if JSON_FILE.exists():
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Must not have any personal name or personal resume text
            assert data.get("name") in ("", None)
            assert data.get("raw_resume_text") in ("", None)


def test_load_profile_from_json_empty_safety():
    """Ensure load_profile_from_json returns None when template/file has empty candidate name."""
    profile = load_profile_from_json()
    assert profile is None


def test_clear_profile_from_json_and_db(tmp_path):
    """Test clearing profile from JSON and SQLite table."""
    test_json = tmp_path / "test_user_profile.json"
    test_db = tmp_path / "test_job_finder.db"

    # Save a temporary profile
    p = UserProfile(name="Temporary User", skills=["Python"], raw_resume_text="Resume text")
    save_profile_to_json(p, file_path=test_json)
    save_profile_to_db(p, db_path=test_db)

    # Verify saved
    loaded = load_profile_from_json(file_path=test_json)
    assert loaded is not None
    assert loaded.name == "Temporary User"

    # Clear JSON and DB
    clear_profile_from_json(file_path=test_json)
    clear_all_profiles_from_db(db_path=test_db)

    # Verify cleared
    assert load_profile_from_json(file_path=test_json) is None


def test_vector_store_delete_and_clear_resumes():
    """Verify ChromaDB resumes can be deleted and cleared without persisting across sessions."""
    store_resume_vector("Privacy Test User", "Resume content for testing privacy")
    store = get_vector_store()
    doc_id = "resume_privacy_test_user"
    assert doc_id in store.collection.get()["ids"]

    # Delete single user vector
    delete_resume_vector("Privacy Test User")
    assert doc_id not in store.collection.get()["ids"]

    # Clear all vectors
    clear_all_resume_vectors()
    assert len(store.collection.get()["ids"]) == 0


def test_run_pipeline_main_does_not_persist_profile_to_json(monkeypatch):
    """Verify run_pipeline.main accepts a session-passed profile without writing it to user_profile.json."""
    from run_pipeline import main

    # Mock ping_mcp_tools, store_resume_vector and graph invoke to run fast unit test
    monkeypatch.setattr("run_pipeline.ping_mcp_tools", lambda: {})
    monkeypatch.setattr("run_pipeline.store_resume_vector", lambda **kwargs: "mock_doc")
    monkeypatch.setattr("run_pipeline.app_graph.invoke", lambda state: {"shortlist": [], "run_id": "test_run"})

    session_profile = UserProfile(
        name="Session Only Candidate",
        skills=["Python", "FastAPI"],
        preferred_roles=["Backend Developer"],
    )

    main(profile=session_profile)

    # Verify user_profile.json on disk was NOT overwritten with Session Only Candidate
    disk_profile = load_profile_from_json()
    assert disk_profile is None


def test_load_shortlist_from_db_does_not_autoseed_on_fresh_startup(tmp_path):
    """Verify that load_shortlist_from_db does not automatically inject seed jobs into empty database."""
    from storage.job_storage import load_shortlist_from_db, init_jobs_db
    test_db = tmp_path / "empty_jobs.db"
    init_jobs_db(test_db)

    jobs = load_shortlist_from_db(db_path=test_db)
    assert jobs == []
    assert len(jobs) == 0


def test_clear_all_shortlisted_jobs(tmp_path):
    """Verify clear_all_shortlisted_jobs removes all stored jobs."""
    from storage.job_storage import save_shortlist_to_db, load_shortlist_from_db, clear_all_shortlisted_jobs
    test_db = tmp_path / "clear_test.db"

    sample_jobs = [{
        "title": "Software Engineer",
        "company": "Infosys",
        "location": "Bengaluru, India",
        "source": "LinkedIn",
        "evaluation": {"match_score": 85, "recommendation": "APPLY", "one_line_reasoning": "Great fit"}
    }]
    run_id = save_shortlist_to_db(sample_jobs, db_path=test_db)
    assert len(load_shortlist_from_db(run_id=run_id, db_path=test_db)) == 1

    clear_all_shortlisted_jobs(db_path=test_db)
    assert len(load_shortlist_from_db(run_id=run_id, db_path=test_db)) == 0


def test_has_active_resume():
    """Verify resume upload / active resume validation logic."""
    from ui.app import has_active_resume

    # Empty candidate profile
    empty_p = UserProfile(name="", skills=[], raw_resume_text="")
    assert has_active_resume(empty_p) is False

    # Default placeholder candidate with no raw resume
    default_p = UserProfile(name="Candidate", skills=["Python"], raw_resume_text="")
    assert has_active_resume(default_p) is False

    # Candidate with raw resume text
    resume_p = UserProfile(name="Candidate", skills=["Python"], raw_resume_text="Experienced engineer with Python skills...")
    assert has_active_resume(resume_p) is True

    # Real candidate with profile details configured
    named_p = UserProfile(name="Aarav Sharma", skills=["Python", "FastAPI"])
    assert has_active_resume(named_p) is True

