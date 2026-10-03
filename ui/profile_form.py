import streamlit as st
from profile.user_profile import UserProfile
from storage.profile_storage import (
    save_profile_to_json,
    save_profile_to_db,
    load_profile_from_json,
)

st.set_page_config(page_title="User Profile Form", page_icon="👤")

st.title("👤 Job Finder - User Profile")

# Load existing profile if available
existing_profile = load_profile_from_json()

with st.form("user_profile_form"):
    name = st.text_input(
        "Full Name", value=existing_profile.name if existing_profile else ""
    )
    skills = st.text_input(
        "Skills (comma-separated)",
        value=", ".join(existing_profile.skills) if existing_profile else "",
    )
    preferred_roles = st.text_input(
        "Preferred Roles (comma-separated)",
        value=", ".join(existing_profile.preferred_roles)
        if existing_profile
        else "",
    )
    experience_years = st.number_input(
        "Years of Experience",
        min_value=0.0,
        max_value=50.0,
        value=existing_profile.experience_years if existing_profile else 0.0,
        step=0.5,
    )

    col1, col2 = st.columns(2)
    with col1:
        min_salary = st.number_input(
            "Minimum Salary",
            min_value=0.0,
            value=existing_profile.min_salary or 0.0 if existing_profile else 0.0,
            step=5000.0,
        )
    with col2:
        max_salary = st.number_input(
            "Maximum Salary",
            min_value=0.0,
            value=existing_profile.max_salary or 0.0 if existing_profile else 0.0,
            step=5000.0,
        )

    locations = st.text_input(
        "Preferred Locations (comma-separated)",
        value=", ".join(existing_profile.locations) if existing_profile else "",
    )
    remote_ok = st.checkbox(
        "Open to Remote Roles",
        value=existing_profile.remote_ok if existing_profile else True,
    )

    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        submitted = st.form_submit_button("💾 Save Profile")
    with c_btn2:
        cleared = st.form_submit_button("🧹 Clear Form Details")

    if submitted:
        if not name:
            st.error("Name is required.")
        else:
            profile = UserProfile(
                name=name,
                skills=[s.strip() for s in skills.split(",") if s.strip()],
                preferred_roles=[
                    r.strip() for r in preferred_roles.split(",") if r.strip()
                ],
                experience_years=experience_years,
                min_salary=min_salary if min_salary > 0 else None,
                max_salary=max_salary if max_salary > 0 else None,
                locations=[l.strip() for l in locations.split(",") if l.strip()],
                remote_ok=remote_ok,
            )
            save_profile_to_json(profile)
            save_profile_to_db(profile)
            st.success("Profile saved successfully to JSON and SQLite!")
            st.rerun()

    if cleared:
        empty_profile = UserProfile(
            name="",
            skills=[],
            preferred_roles=[],
            experience_years=0.0,
            min_salary=0.0,
            max_salary=0.0,
            locations=[],
            remote_ok=True,
            raw_resume_text="",
        )
        save_profile_to_json(empty_profile)
        save_profile_to_db(empty_profile)
        st.toast("Candidate profile cleared!", icon="🧹")
        st.rerun()
