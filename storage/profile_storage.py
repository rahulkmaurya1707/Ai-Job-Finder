import json
import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any
from profile.user_profile import UserProfile
from profile.resume_analyzer import StructuredResumeData

STORAGE_DIR = Path(__file__).resolve().parent
JSON_FILE = STORAGE_DIR / "user_profile.json"
DB_FILE = STORAGE_DIR / "job_finder.db"


def init_db(db_path: Path = DB_FILE) -> None:
    """Initialize SQLite database schema creating the profiles table."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                skills TEXT,
                preferred_roles TEXT,
                experience_years REAL,
                min_salary REAL,
                max_salary REAL,
                locations TEXT,
                remote_ok INTEGER,
                resume_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()


def save_profile_to_db(
    profile: UserProfile,
    resume_data: Optional[StructuredResumeData] = None,
    db_path: Path = DB_FILE,
) -> None:
    """Save UserProfile and structured resume JSON into the profiles table."""
    init_db(db_path)
    resume_json = (
        resume_data.model_dump_json()
        if resume_data
        else (
            json.dumps(resume_data)
            if isinstance(resume_data, dict)
            else None
        )
    )

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        # Delete previous entries for the same user name to keep latest profile
        cursor.execute("DELETE FROM profiles WHERE name = ?", (profile.name,))
        cursor.execute(
            """
            INSERT INTO profiles (
                name, skills, preferred_roles, experience_years,
                min_salary, max_salary, locations, remote_ok, resume_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                profile.name,
                json.dumps(profile.skills),
                json.dumps(profile.preferred_roles),
                profile.experience_years,
                profile.min_salary,
                profile.max_salary,
                json.dumps(profile.locations),
                1 if profile.remote_ok else 0,
                resume_json,
            ),
        )
        conn.commit()


def load_profile_from_db(
    name: str, db_path: Path = DB_FILE
) -> Optional[Dict[str, Any]]:
    """Fetch user profile and structured resume data from profiles table."""
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM profiles WHERE name = ? ORDER BY id DESC LIMIT 1",
            (name,),
        )
        row = cursor.fetchone()
        if row:
            profile = UserProfile(
                name=row["name"],
                skills=json.loads(row["skills"]) if row["skills"] else [],
                preferred_roles=json.loads(row["preferred_roles"])
                if row["preferred_roles"]
                else [],
                experience_years=row["experience_years"] or 0.0,
                min_salary=row["min_salary"],
                max_salary=row["max_salary"],
                locations=json.loads(row["locations"]) if row["locations"] else [],
                remote_ok=bool(row["remote_ok"]),
            )
            resume_data = (
                StructuredResumeData.model_validate_json(row["resume_data"])
                if row["resume_data"]
                else None
            )
            return {"profile": profile, "resume_data": resume_data}
    return None


def save_profile_to_json(
    profile: UserProfile, file_path: Path = JSON_FILE
) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(profile.model_dump(), f, indent=2)


def load_profile_from_json(file_path: Path = JSON_FILE) -> Optional[UserProfile]:
    if not file_path.exists():
        return None
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        return UserProfile(**data)
