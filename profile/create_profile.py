from profile.user_profile import UserProfile
from storage.profile_storage import save_profile_to_json, save_profile_to_db
from config import get_logger

logger = get_logger("create_profile")


def collect_profile_interactively() -> UserProfile:
    logger.info("--- User Profile Collector ---")
    name = input("Enter your name: ").strip() or "User"
    skills_raw = input("Enter skills (comma separated): ").strip()
    skills = [s.strip() for s in skills_raw.split(",") if s.strip()]

    roles_raw = input(
        "Enter preferred roles (comma separated): "
    ).strip()
    preferred_roles = [r.strip() for r in roles_raw.split(",") if r.strip()]

    exp_raw = input("Years of experience (default 0): ").strip()
    experience_years = float(exp_raw) if exp_raw else 0.0

    min_sal_raw = input("Minimum salary (optional, default 0): ").strip()
    min_salary = float(min_sal_raw) if min_sal_raw else None

    max_sal_raw = input("Maximum salary (optional, default 0): ").strip()
    max_salary = float(max_sal_raw) if max_sal_raw else None

    loc_raw = input("Preferred locations (comma separated): ").strip()
    locations = [l.strip() for l in loc_raw.split(",") if l.strip()]

    remote_raw = input("Remote OK? (y/n, default y): ").strip().lower()
    remote_ok = remote_raw != "n"

    profile = UserProfile(
        name=name,
        skills=skills,
        preferred_roles=preferred_roles,
        experience_years=experience_years,
        min_salary=min_salary,
        max_salary=max_salary,
        locations=locations,
        remote_ok=remote_ok,
    )

    save_profile_to_json(profile)
    save_profile_to_db(profile)
    logger.info("Profile saved successfully to JSON and SQLite database!")
    return profile


if __name__ == "__main__":
    collect_profile_interactively()
