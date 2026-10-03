import json
import sqlite3
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

STORAGE_DIR = Path(__file__).resolve().parent
DB_FILE = STORAGE_DIR / "job_finder.db"


def init_jobs_db(db_path: Path = DB_FILE) -> None:
    """Initialize SQLite database tables for evaluated jobs and final shortlists."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        # Table for evaluated jobs
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS evaluated_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hash_key TEXT UNIQUE,
                title TEXT NOT NULL,
                company TEXT,
                location TEXT,
                description TEXT,
                posted_date TEXT,
                apply_url TEXT,
                source TEXT,
                vector_similarity_score REAL,
                match_score INTEGER,
                matching_skills TEXT,
                missing_skills TEXT,
                recommendation TEXT,
                one_line_reasoning TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Table for final shortlists with run_id and timestamp
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS shortlisted_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                user_name TEXT,
                hash_key TEXT,
                title TEXT NOT NULL,
                company TEXT,
                location TEXT,
                description TEXT,
                posted_date TEXT,
                apply_url TEXT,
                source TEXT,
                vector_similarity_score REAL,
                match_score INTEGER,
                recommendation TEXT,
                one_line_reasoning TEXT,
                is_seen INTEGER DEFAULT 0,
                is_applied INTEGER DEFAULT 0,
                status TEXT DEFAULT 'new',
                status_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                cover_letter_draft TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # Migration check for existing databases
        cursor.execute("PRAGMA table_info(shortlisted_jobs)")
        existing_cols = [row[1] for row in cursor.fetchall()]
        if "is_seen" not in existing_cols:
            cursor.execute("ALTER TABLE shortlisted_jobs ADD COLUMN is_seen INTEGER DEFAULT 0")
        if "is_applied" not in existing_cols:
            cursor.execute("ALTER TABLE shortlisted_jobs ADD COLUMN is_applied INTEGER DEFAULT 0")
        if "status" not in existing_cols:
            cursor.execute("ALTER TABLE shortlisted_jobs ADD COLUMN status TEXT DEFAULT 'new'")
        if "status_updated_at" not in existing_cols:
            cursor.execute("ALTER TABLE shortlisted_jobs ADD COLUMN status_updated_at TIMESTAMP DEFAULT NULL")
        if "cover_letter_draft" not in existing_cols:
            cursor.execute("ALTER TABLE shortlisted_jobs ADD COLUMN cover_letter_draft TEXT")

        # Table for recording final job application outcomes (rejected/offer)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS job_outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER,
                hash_key TEXT,
                title TEXT NOT NULL,
                company TEXT,
                location TEXT,
                outcome TEXT NOT NULL,
                original_match_score INTEGER,
                matching_skills TEXT,
                missing_skills TEXT,
                outcome_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()


def save_evaluated_jobs(
    jobs: List[Dict[str, Any]], db_path: Path = DB_FILE
) -> None:
    """Save or update structured evaluation results for top jobs into SQLite database."""
    init_jobs_db(db_path)
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        for job in jobs:
            eval_data = job.get("evaluation", {})
            matching_skills_json = json.dumps(
                eval_data.get("matching_skills", [])
                if isinstance(eval_data, dict)
                else getattr(eval_data, "matching_skills", [])
            )
            missing_skills_json = json.dumps(
                eval_data.get("missing_skills", [])
                if isinstance(eval_data, dict)
                else getattr(eval_data, "missing_skills", [])
            )
            match_score = (
                eval_data.get("match_score", 0)
                if isinstance(eval_data, dict)
                else getattr(eval_data, "match_score", 0)
            )
            recommendation = str(
                eval_data.get("recommendation", "Skip")
                if isinstance(eval_data, dict)
                else getattr(eval_data, "recommendation", "Skip")
            )
            reasoning = str(
                eval_data.get("one_line_reasoning", "")
                if isinstance(eval_data, dict)
                else getattr(eval_data, "one_line_reasoning", "")
            )

            cursor.execute(
                """
                INSERT INTO evaluated_jobs (
                    hash_key, title, company, location, description, posted_date,
                    apply_url, source, vector_similarity_score, match_score,
                    matching_skills, missing_skills, recommendation, one_line_reasoning
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(hash_key) DO UPDATE SET
                    match_score=excluded.match_score,
                    matching_skills=excluded.matching_skills,
                    missing_skills=excluded.missing_skills,
                    recommendation=excluded.recommendation,
                    one_line_reasoning=excluded.one_line_reasoning
                """,
                (
                    job.get("hash_key", ""),
                    job.get("title", ""),
                    job.get("company", ""),
                    job.get("location", ""),
                    job.get("description", ""),
                    job.get("posted_date", ""),
                    job.get("apply_url", ""),
                    job.get("source", ""),
                    job.get("similarity_score", 0.0),
                    match_score,
                    matching_skills_json,
                    missing_skills_json,
                    recommendation,
                    reasoning,
                ),
            )
        conn.commit()


def save_shortlist_to_db(
    shortlist_jobs: List[Dict[str, Any]],
    run_id: Optional[str] = None,
    user_name: str = "User",
    db_path: Path = DB_FILE,
) -> str:
    """Store the final shortlist in SQLite along with a run_id and timestamp."""
    init_jobs_db(db_path)
    current_run_id = run_id or f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        for job in shortlist_jobs:
            eval_data = job.get("evaluation", {})
            matching_skills_json = json.dumps(
                eval_data.get("matching_skills", [])
                if isinstance(eval_data, dict)
                else getattr(eval_data, "matching_skills", [])
            )
            missing_skills_json = json.dumps(
                eval_data.get("missing_skills", [])
                if isinstance(eval_data, dict)
                else getattr(eval_data, "missing_skills", [])
            )
            match_score = (
                eval_data.get("match_score", 0)
                if isinstance(eval_data, dict)
                else getattr(eval_data, "match_score", 0)
            )
            recommendation = str(
                eval_data.get("recommendation", "Skip")
                if isinstance(eval_data, dict)
                else getattr(eval_data, "recommendation", "Skip")
            )
            reasoning = str(
                eval_data.get("one_line_reasoning", "")
                if isinstance(eval_data, dict)
                else getattr(eval_data, "one_line_reasoning", "")
            )

            cursor.execute(
                """
                INSERT INTO shortlisted_jobs (
                    run_id, user_name, hash_key, title, company, location,
                    description, posted_date, apply_url, source, vector_similarity_score,
                    match_score, recommendation, one_line_reasoning, matching_skills, missing_skills, cover_letter_draft
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    current_run_id,
                    user_name,
                    job.get("hash_key", ""),
                    job.get("title", ""),
                    job.get("company", ""),
                    job.get("location", ""),
                    job.get("description", ""),
                    job.get("posted_date", ""),
                    job.get("apply_url", ""),
                    job.get("source", ""),
                    job.get("similarity_score", 0.0),
                    match_score,
                    recommendation,
                    reasoning,
                    matching_skills_json,
                    missing_skills_json,
                    job.get("cover_letter_draft") or (eval_data.get("cover_letter_draft") if isinstance(eval_data, dict) else ""),
                ),
            )
        conn.commit()
    return current_run_id


def load_shortlist_from_db(
    run_id: Optional[str] = None, db_path: Path = DB_FILE
) -> List[Dict[str, Any]]:
    """Retrieve shortlisted jobs from SQLite database for a specific run_id or latest run."""
    init_jobs_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if run_id:
            cursor.execute(
                "SELECT * FROM shortlisted_jobs WHERE run_id = ? ORDER BY match_score DESC",
                (run_id,),
            )
        else:
            # Query latest run_id
            cursor.execute(
                "SELECT * FROM shortlisted_jobs WHERE run_id = (SELECT run_id FROM shortlisted_jobs ORDER BY id DESC LIMIT 1) ORDER BY match_score DESC"
            )
        rows = cursor.fetchall()
        jobs = []
        for row in rows:
            jobs.append(
                {
                    "id": row["id"],
                    "run_id": row["run_id"],
                    "user_name": row["user_name"],
                    "hash_key": row["hash_key"],
                    "title": row["title"],
                    "company": row["company"],
                    "location": row["location"],
                    "description": row["description"],
                    "posted_date": row["posted_date"],
                    "apply_url": row["apply_url"],
                    "source": row["source"],
                    "similarity_score": row["vector_similarity_score"],
                    "is_seen": bool(row["is_seen"]) if "is_seen" in row.keys() else False,
                    "is_applied": bool(row["is_applied"]) if "is_applied" in row.keys() else False,
                    "status": (row["status"] if "status" in row.keys() and row["status"] else "new").lower(),
                    "status_updated_at": row["status_updated_at"] if "status_updated_at" in row.keys() else row["created_at"],
                    "cover_letter_draft": row["cover_letter_draft"] if "cover_letter_draft" in row.keys() and row["cover_letter_draft"] else "",
                    "created_at": row["created_at"],
                    "evaluation": {
                        "match_score": row["match_score"],
                        "recommendation": row["recommendation"],
                        "one_line_reasoning": row["one_line_reasoning"],
                        "matching_skills": json.loads(row["matching_skills"])
                        if row["matching_skills"]
                        else [],
                        "missing_skills": json.loads(row["missing_skills"])
                        if row["missing_skills"]
                        else [],
                        "cover_letter_draft": row["cover_letter_draft"] if "cover_letter_draft" in row.keys() and row["cover_letter_draft"] else "",
                    },
                }
            )
        return jobs


def get_all_run_ids(db_path: Path = DB_FILE) -> List[str]:
    """Retrieve distinct run_ids ordered by latest creation."""
    init_jobs_db(db_path)
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT run_id FROM shortlisted_jobs ORDER BY id DESC")
        return [row[0] for row in cursor.fetchall() if row[0]]


VALID_STATUSES = ["new", "seen", "applied", "interviewing", "rejected", "offer"]


def update_job_full_status(
    job_db_id: int,
    new_status: str,
    db_path: Path = DB_FILE,
) -> None:
    """Update job application status ('new', 'seen', 'applied', 'interviewing', 'rejected', 'offer') with timestamp recording."""
    status_clean = str(new_status).lower().strip()
    if status_clean not in VALID_STATUSES:
        raise ValueError(f"Invalid status '{new_status}'. Must be one of {VALID_STATUSES}")

    init_jobs_db(db_path)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    is_seen_val = 1 if status_clean in ["seen", "applied", "interviewing", "offer", "rejected"] else 0
    is_applied_val = 1 if status_clean in ["applied", "interviewing", "offer", "rejected"] else 0

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE shortlisted_jobs
            SET status = ?, is_seen = ?, is_applied = ?, status_updated_at = ?
            WHERE id = ?
            """,
            (status_clean, is_seen_val, is_applied_val, now_str, job_db_id),
        )
        conn.commit()

    if status_clean in ["rejected", "offer"]:
        record_job_outcome(job_db_id, status_clean, db_path=db_path)


def record_job_outcome(
    job_db_id: int, outcome: str, db_path: Path = DB_FILE
) -> None:
    """Record job outcome ('rejected' or 'offer') alongside original match score and matching/missing skills in SQLite."""
    outcome_clean = str(outcome).lower().strip()
    if outcome_clean not in ["rejected", "offer"]:
        return

    init_jobs_db(db_path)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM shortlisted_jobs WHERE id = ?", (job_db_id,))
        row = cursor.fetchone()
        if row:
            cursor.execute(
                """
                INSERT INTO job_outcomes (
                    job_id, hash_key, title, company, location, outcome,
                    original_match_score, matching_skills, missing_skills, outcome_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["id"],
                    row["hash_key"],
                    row["title"],
                    row["company"],
                    row["location"],
                    outcome_clean,
                    row["match_score"],
                    row["matching_skills"],
                    row["missing_skills"],
                    now_str,
                ),
            )
            conn.commit()


def get_job_outcomes(db_path: Path = DB_FILE) -> List[Dict[str, Any]]:
    """Retrieve recorded application outcomes (rejected/offer) with original match scores and skills."""
    init_jobs_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM job_outcomes ORDER BY outcome_date DESC")
        rows = cursor.fetchall()
        outcomes = []
        for row in rows:
            outcomes.append(
                {
                    "id": row["id"],
                    "job_id": row["job_id"],
                    "hash_key": row["hash_key"],
                    "title": row["title"],
                    "company": row["company"],
                    "location": row["location"],
                    "outcome": row["outcome"],
                    "original_match_score": row["original_match_score"],
                    "matching_skills": json.loads(row["matching_skills"])
                    if row["matching_skills"]
                    else [],
                    "missing_skills": json.loads(row["missing_skills"])
                    if row["missing_skills"]
                    else [],
                    "outcome_date": row["outcome_date"],
                }
            )
        return outcomes


def update_shortlist_job_status(
    job_db_id: int,
    is_seen: Optional[bool] = None,
    is_applied: Optional[bool] = None,
    db_path: Path = DB_FILE,
) -> None:
    """Update is_seen or is_applied status of a shortlisted job in SQLite database."""
    init_jobs_db(db_path)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        if is_seen is not None:
            status_val = "seen" if is_seen else "new"
            cursor.execute(
                "UPDATE shortlisted_jobs SET is_seen = ?, status = ?, status_updated_at = ? WHERE id = ?",
                (1 if is_seen else 0, status_val, now_str, job_db_id),
            )
        if is_applied is not None:
            status_val = "applied" if is_applied else "seen"
            cursor.execute(
                "UPDATE shortlisted_jobs SET is_applied = ?, status = ?, status_updated_at = ? WHERE id = ?",
                (1 if is_applied else 0, status_val, now_str, job_db_id),
            )
        conn.commit()


def get_application_analytics(db_path: Path = DB_FILE) -> Dict[str, Any]:
    """Calculate application metrics:
    - Average score of applied jobs
    - Average score of jobs that got interviews/offers
    - Frequently missing skills in rejected applications
    - Status breakdown counts
    """
    init_jobs_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM shortlisted_jobs")
        all_jobs = cursor.fetchall()

        cursor.execute("SELECT * FROM job_outcomes")
        all_outcomes = cursor.fetchall()

    applied_scores = []
    interview_offer_scores = []
    status_counts = Counter()
    rejection_missing_skills_counter = Counter()

    for job in all_jobs:
        st_val = (job["status"] if "status" in job.keys() and job["status"] else "new").lower()
        status_counts[st_val] += 1
        score = job["match_score"] or 0

        if st_val in ["applied", "interviewing", "rejected", "offer"] or (
            "is_applied" in job.keys() and job["is_applied"]
        ):
            applied_scores.append(score)

        if st_val in ["interviewing", "offer"]:
            interview_offer_scores.append(score)

        if st_val == "rejected":
            missing = (
                json.loads(job["missing_skills"])
                if "missing_skills" in job.keys() and job["missing_skills"]
                else []
            )
            for sk in missing:
                rejection_missing_skills_counter[sk.strip()] += 1

    for outcome in all_outcomes:
        out_type = (outcome["outcome"] or "").lower()
        score = outcome["original_match_score"] or 0
        if out_type == "offer":
            interview_offer_scores.append(score)
        elif out_type == "rejected":
            missing = (
                json.loads(outcome["missing_skills"])
                if outcome["missing_skills"]
                else []
            )
            for sk in missing:
                rejection_missing_skills_counter[sk.strip()] += 1

    avg_applied = (
        round(sum(applied_scores) / len(applied_scores), 1)
        if applied_scores
        else None
    )
    avg_interview_offer = (
        round(sum(interview_offer_scores) / len(interview_offer_scores), 1)
        if interview_offer_scores
        else None
    )

    most_common_rejection_skills = rejection_missing_skills_counter.most_common(10)

    return {
        "avg_applied_score": avg_applied,
        "avg_interview_offer_score": avg_interview_offer,
        "total_applied_count": len(applied_scores),
        "total_interview_offer_count": len(interview_offer_scores),
        "frequent_rejection_missing_skills": most_common_rejection_skills,
        "status_counts": dict(status_counts),
    }


def get_recommended_profile_skills(
    current_skills: List[str], min_occurrences: int = 1, db_path: Path = DB_FILE
) -> List[Dict[str, Any]]:
    """Identify missing skills that repeatedly appear across good-fit jobs (match_score >= 60)
    and are not currently listed in the candidate's profile skills.
    """
    init_jobs_db(db_path)
    current_skills_set = {
        s.lower().strip() for s in current_skills if isinstance(s, str) and s.strip()
    }

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT missing_skills FROM shortlisted_jobs WHERE match_score >= 60"
        )
        rows = cursor.fetchall()

    skill_counts = Counter()
    for row in rows:
        missing = (
            json.loads(row["missing_skills"])
            if "missing_skills" in row.keys() and row["missing_skills"]
            else []
        )
        for sk in missing:
            clean_sk = sk.strip()
            if clean_sk and clean_sk.lower() not in current_skills_set:
                skill_counts[clean_sk] += 1

    recommendations = []
    for sk, count in skill_counts.most_common(10):
        if count >= min_occurrences:
            recommendations.append({"skill": sk, "occurrences": count})

    return recommendations
