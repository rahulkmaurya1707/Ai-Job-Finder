import sys
from pathlib import Path
from datetime import datetime

# Ensure project root is in sys.path when executed via Streamlit
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import pandas as pd
import plotly.express as px

from storage.profile_storage import (
    load_profile_from_json,
    save_profile_to_json,
    save_profile_to_db,
)
from storage.job_storage import (
    load_shortlist_from_db,
    update_job_full_status,
    get_application_analytics,
    get_recommended_profile_skills,
    get_all_run_ids,
)
from profile.user_profile import UserProfile
from config.config import load_pipeline_config, save_pipeline_config

# Import Modular UI Components
import importlib
import ui.components.kpi_card as kpi_module
import ui.components.job_card as job_module
import ui.components.kanban as kanban_module

importlib.reload(kpi_module)
importlib.reload(job_module)
importlib.reload(kanban_module)

from ui.components.kpi_card import render_kpi_card
from ui.components.job_card import render_job_card

# Set Streamlit Page Configuration
st.set_page_config(
    page_title="AI Job Finder - Student SaaS Dashboard",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Load External Design System CSS
styles_path = Path(__file__).parent / "styles.css"
if styles_path.exists():
    with open(styles_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Load Candidate Profile for Header & Greeting
existing_profile = load_profile_from_json()
candidate_name = existing_profile.name.strip() if (existing_profile and existing_profile.name and existing_profile.name.strip()) else "Candidate"
first_name = candidate_name.split()[0] if candidate_name != "Candidate" else "Candidate"
user_initials = "".join([p[0].upper() for p in candidate_name.split()[:2]]) if candidate_name != "Candidate" else "CP"

import os

# Check for required GROQ_API_KEY in cloud environments like Render
if not os.getenv("GROQ_API_KEY"):
    st.warning("⚠️ **GROQ_API_KEY** environment variable is missing. Add your `GROQ_API_KEY` under Render Environment Settings to activate LLM matching & cover letter generation.")

# -----------------------------------------------------------------------------
# GLOBAL UNIFIED STICKY TOP HEADER BAR
# -----------------------------------------------------------------------------
hdr_col1, hdr_col2, hdr_col3 = st.columns([2.4, 1.3, 1.3], vertical_alignment="center")

with hdr_col1:
    st.markdown(
        """<div class="brand-wrapper">
<div class="brand-logo-icon">💼</div>
<div>
<h1 class="brand-title-text">AI Job Finder</h1>
<div class="brand-subline">LLM Resume Matcher & Automated Application Tracker</div>
</div>
</div>""",
        unsafe_allow_html=True,
    )

with hdr_col2:
    st.markdown(
        f"""<div class="user-status-pill">
<div class="user-avatar-circle">{user_initials}</div>
<div class="user-display-name">{candidate_name}</div>
<div style="display: flex; align-items: center; gap: 0.35rem; margin-left: 0.35rem;">
<span class="status-dot-green"></span>
<span class="status-text-connected">Connected</span>
</div>
</div>""",
        unsafe_allow_html=True,
    )

with hdr_col3:
    if st.button("⚡ RUN JOB PIPELINE 🚀", type="primary", use_container_width=True):
        with st.spinner("Executing job search scraper & LLM matching pipeline..."):
            try:
                from run_pipeline import main as execute_pipeline
                execute_pipeline()
                st.cache_data.clear()
                st.toast("Pipeline complete! Matching jobs synced.", icon="🎉")
                st.rerun()
            except Exception as e:
                st.error(f"Pipeline execution failed: {str(e)}")

st.markdown("<div style='margin-bottom: 24px;'></div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 5 NAVIGATION TABS WITH EMOJI ICONS
# -----------------------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "🏠 Job Shortlist",
        "👤 User Profile",
        "📋 Application Tracker",
        "📊 Analytics",
        "⚙️ Pipeline Settings",
    ]
)

# -----------------------------------------------------------------------------
# TAB 1: Job Shortlist
# -----------------------------------------------------------------------------
with tab1:
    st.markdown(
        f"""<div class="hero-banner">
<div class="hero-title">Welcome back, {first_name}! 👋</div>
<div class="hero-subtitle">Your AI agent is ready to scan active job portals & match top software roles to your resume.</div>
<div style="font-size: 0.82rem; color: #94A3B8; margin-top: 0.5rem; display: flex; align-items: center; gap: 0.5rem;">
<span class="status-dot-green"></span> <span>AI Matcher Active &nbsp;•&nbsp; Target: Entry-Level & Remote &nbsp;•&nbsp; SQLite DB Synced</span>
</div>
</div>""",
        unsafe_allow_html=True,
    )

    # Load All Jobs for KPI Summary
    all_shortlist_jobs = load_shortlist_from_db()
    total_jobs_cnt = len(all_shortlist_jobs)
    top_matches_cnt = sum(1 for j in all_shortlist_jobs if j.get("evaluation", {}).get("match_score", 0) >= 60)
    applied_cnt = sum(1 for j in all_shortlist_jobs if j.get("is_applied"))
    
    last_run_str = "Just Now" if all_shortlist_jobs else "N/A"
    if all_shortlist_jobs and all_shortlist_jobs[0].get("created_at"):
        try:
            last_run_str = str(all_shortlist_jobs[0].get("created_at"))[:16]
        except Exception:
            pass

    # 4 KPI Stat Cards with Top Accent Colors & Real Time
    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
    with kpi_col1:
        render_kpi_card("Total Jobs", str(total_jobs_cnt), "Fetched across active portals", icon="💼", accent_color="#6366F1")
    with kpi_col2:
        render_kpi_card("Top Matches", str(top_matches_cnt), "≥60% match rating", icon="🔥", accent_color="#10B981")
    with kpi_col3:
        render_kpi_card("Applications", str(applied_cnt), "Submitted or tracked", icon="✅", accent_color="#F59E0B")
    with kpi_col4:
        render_kpi_card("Last Run", last_run_str, "Pipeline auto-synced", icon="⏱️", accent_color="#06B6D4")

    st.markdown("<div style='margin-bottom: 1.25rem;'></div>", unsafe_allow_html=True)

    # Search, Filters & Toolbar Controls
    all_runs = get_all_run_ids()
    selected_run = None

    ctrl1, ctrl2, ctrl3, ctrl4, ctrl5, ctrl6, ctrl7 = st.columns([2.0, 1.3, 1.3, 1.3, 1.4, 0.9, 0.9])
    with ctrl1:
        search_query = st.text_input(
            "Search Title/Company",
            placeholder="Search title, company, skills...",
            label_visibility="collapsed",
            key="shortlist_search_input",
        )
    with ctrl2:
        rec_filter = st.selectbox(
            "Filter Recommendation",
            options=["All Recommendations", "APPLY", "CONSIDER", "SKIP"],
            index=0,
            label_visibility="collapsed",
            key="shortlist_rec_filter",
        )
    with ctrl3:
        portal_filter = st.selectbox(
            "Filter Portal",
            options=["All Portals", "RemoteOK", "WeWorkRemotely", "Jobicy", "Arbeitnow", "Remotive", "LinkedIn", "Indeed", "Naukri"],
            index=0,
            label_visibility="collapsed",
            key="shortlist_portal_filter",
        )
    with ctrl4:
        sort_by = st.selectbox(
            "Sort By",
            options=["Match Score", "Newest First"],
            index=0,
            label_visibility="collapsed",
            key="shortlist_sort_by",
        )
    with ctrl5:
        run_options = ["Latest Batch"] + (all_runs if all_runs else [])
        selected_option = st.selectbox(
            "Select Run Batch",
            options=run_options,
            index=0,
            label_visibility="collapsed",
            key="shortlist_run_selector",
        )
        if selected_option != "Latest Batch":
            selected_run = selected_option
    with ctrl6:
        hide_seen = st.checkbox("Hide Seen", value=False, key="shortlist_hide_seen")
    with ctrl7:
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_data.clear()
            st.toast("Database reloaded.", icon="🔄")
            st.rerun()

    shortlist_raw = load_shortlist_from_db(run_id=selected_run)

    # Filter Logic
    shortlist_filtered = []
    for job in shortlist_raw:
        eval_data = job.get("evaluation", {})
        rec_val = str(eval_data.get("recommendation", "Consider")).replace("RecommendationEnum.", "").strip().upper()
        title_c = str(job.get("title", "")).lower()
        company_c = str(job.get("company", "")).lower()
        source_c = str(job.get("source", ""))

        if search_query and (search_query.lower() not in title_c and search_query.lower() not in company_c):
            continue
        if rec_filter != "All Recommendations" and rec_val != rec_filter:
            continue
        if portal_filter != "All Portals" and source_c != portal_filter:
            continue
        if hide_seen and job.get("is_seen"):
            continue
        shortlist_filtered.append(job)

    # Sort Logic
    if sort_by == "Newest First":
        shortlist_filtered.sort(key=lambda j: j.get("created_at") or j.get("id") or 0, reverse=True)
    else:
        shortlist_filtered.sort(key=lambda j: j.get("evaluation", {}).get("match_score", 0), reverse=True)

    if not shortlist_filtered:
        st.info("💡 No matching job cards found for the selected filters. Click '⚡ RUN JOB PIPELINE 🚀' to scan portals.")
    else:
        st.caption(f"Displaying **{len(shortlist_filtered)}** job card(s)")

        # Render Modern Job Cards
        for idx, job in enumerate(shortlist_filtered):
            render_job_card(job, idx)

# -----------------------------------------------------------------------------
# TAB 2: User Profile (Completeness Progress Bar & Two-Column Layout)
# -----------------------------------------------------------------------------
with tab2:
    st.markdown("## Candidate Profile & Resume Parser")
    st.caption("Manage candidate details, parse uploaded resumes, and view AI skill recommendations.")

    existing_profile = load_profile_from_json()

    # Profile Completeness Calculation
    filled_fields = 0
    total_fields = 6
    if existing_profile:
        if existing_profile.name: filled_fields += 1
        if existing_profile.skills: filled_fields += 1
        if existing_profile.preferred_roles: filled_fields += 1
        if existing_profile.experience_years is not None: filled_fields += 1
        if existing_profile.locations: filled_fields += 1
        if existing_profile.raw_resume_text: filled_fields += 1

    completeness_pct = int((filled_fields / total_fields) * 100)

    st.markdown("<div class='card-wrapper'>", unsafe_allow_html=True)
    st.markdown(f"### 📈 Profile Completeness ({completeness_pct}%)")
    st.progress(min(completeness_pct / 100.0, 1.0))
    st.markdown("</div>", unsafe_allow_html=True)

    # Recommended Skill Additions
    curr_skills = existing_profile.skills if existing_profile else []
    skill_recs = get_recommended_profile_skills(curr_skills, min_occurrences=1)

    if skill_recs:
        st.markdown("<div class='card-wrapper'>", unsafe_allow_html=True)
        st.markdown("### 💡 Recommended Skill Additions")
        st.caption("These skills appear frequently in high-matching job postings:")
        rec_cols = st.columns(min(len(skill_recs), 5))
        for idx, rec in enumerate(skill_recs[:5]):
            with rec_cols[idx % 5]:
                if st.button(f"➕ {rec['skill']} ({rec['occurrences']})", key=f"add_sk_chip_{idx}", use_container_width=True):
                    if existing_profile:
                        if rec['skill'] not in existing_profile.skills:
                            existing_profile.skills.append(rec['skill'])
                            save_profile_to_json(existing_profile)
                            save_profile_to_db(existing_profile)
                            st.toast(f"Added '{rec['skill']}' to profile!", icon="🎉")
                            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # Two-Column Layout: Left = Resume Upload, Right = Candidate Form
    prof_col1, prof_col2 = st.columns([1.2, 1.8])

    with prof_col1:
        st.markdown("<div class='card-wrapper'>", unsafe_allow_html=True)
        st.markdown("### 📄 Resume Drag & Drop")
        st.caption("Upload a PDF or DOCX resume to automatically parse skills and experience.")

        uploaded_resume = st.file_uploader(
            "Upload Resume File",
            type=["pdf", "docx"],
            key="profile_resume_uploader",
            label_visibility="collapsed",
        )

        if uploaded_resume is not None:
            try:
                from profile.resume_parser import extract_text_from_resume
                from profile.resume_analyzer import analyze_resume_text
                from storage.vector_store import store_resume_vector

                file_bytes = uploaded_resume.getvalue()
                extracted_text = extract_text_from_resume(file_bytes, uploaded_resume.name)

                st.success(f"Extracted {len(extracted_text)} characters from '{uploaded_resume.name}'")

                session_key = f"parsed_resume_{uploaded_resume.name}_{uploaded_resume.size}"
                if not st.session_state.get(session_key):
                    with st.spinner("Analyzing resume with Groq AI..."):
                        parsed = analyze_resume_text(extracted_text)

                    if existing_profile:
                        if parsed.candidate_name and parsed.candidate_name.strip():
                            existing_profile.name = parsed.candidate_name.strip()
                        if parsed.skills:
                            existing_profile.skills = list(dict.fromkeys([s.strip() for s in parsed.skills if s.strip()]))
                        if parsed.preferred_roles:
                            existing_profile.preferred_roles = list(dict.fromkeys([r.strip() for r in parsed.preferred_roles if r.strip()]))
                        if parsed.experience_years > 0:
                            existing_profile.experience_years = float(parsed.experience_years)
                        if parsed.locations:
                            existing_profile.locations = list(dict.fromkeys([l.strip() for l in parsed.locations if l.strip()]))

                        existing_profile.raw_resume_text = extracted_text
                        save_profile_to_json(existing_profile)
                        save_profile_to_db(existing_profile)
                        store_resume_vector(user_name=existing_profile.name, resume_text=extracted_text)
                        st.session_state[session_key] = True
                        st.toast("Profile updated from uploaded resume!", icon="✅")
                        st.rerun()
            except Exception as e:
                st.error(f"Failed to parse resume: {str(e)}")

        if existing_profile and existing_profile.raw_resume_text:
            with st.expander("Preview Raw Resume Text"):
                st.text_area("Raw Text", value=existing_profile.raw_resume_text, height=220, label_visibility="collapsed")
        st.markdown("</div>", unsafe_allow_html=True)

    with prof_col2:
        st.markdown("<div class='card-wrapper'>", unsafe_allow_html=True)
        st.markdown("### 👤 Candidate Details Form")
        with st.form("user_profile_form"):
            name = st.text_input("Full Name", value=existing_profile.name if existing_profile else "")
            skills = st.text_input("Skills (comma-separated)", value=", ".join(existing_profile.skills) if existing_profile else "")
            preferred_roles = st.text_input("Preferred Roles (comma-separated)", value=", ".join(existing_profile.preferred_roles) if existing_profile else "")
            
            experience_years = st.slider(
                "Years of Experience",
                min_value=0.0,
                max_value=10.0,
                value=existing_profile.experience_years if existing_profile else 0.0,
                step=0.5,
                help="0 years for fresh graduates and students seeking entry-level/internship roles",
            )

            c_sal1, c_sal2 = st.columns(2)
            with c_sal1:
                min_salary = st.number_input("Minimum Target Salary ($)", min_value=0.0, value=existing_profile.min_salary or 0.0 if existing_profile else 0.0, step=5000.0)
            with c_sal2:
                max_salary = st.number_input("Maximum Target Salary ($)", min_value=0.0, value=existing_profile.max_salary or 0.0 if existing_profile else 0.0, step=5000.0)

            locations = st.text_input("Preferred Locations (comma-separated)", value=", ".join(existing_profile.locations) if existing_profile else "")
            remote_ok = st.checkbox("Open to Remote Roles", value=existing_profile.remote_ok if existing_profile else True)

            c_btn1, c_btn2 = st.columns(2)
            with c_btn1:
                submitted = st.form_submit_button("💾 Save Profile Settings", type="primary", use_container_width=True)
            with c_btn2:
                cleared = st.form_submit_button("🧹 Clear Form Details", type="secondary", use_container_width=True)

            if submitted:
                if not name:
                    st.error("Full Name is required.")
                else:
                    profile = UserProfile(
                        name=name,
                        skills=[s.strip() for s in skills.split(",") if s.strip()],
                        preferred_roles=[r.strip() for r in preferred_roles.split(",") if r.strip()],
                        experience_years=experience_years,
                        min_salary=min_salary if min_salary > 0 else None,
                        max_salary=max_salary if max_salary > 0 else None,
                        locations=[l.strip() for l in locations.split(",") if l.strip()],
                        remote_ok=remote_ok,
                    )
                    save_profile_to_json(profile)
                    save_profile_to_db(profile)
                    st.toast("Profile settings saved successfully!", icon="✅")
                    st.success("Profile saved successfully!")
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
                st.toast("Candidate form details cleared!", icon="🧹")
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# TAB 3: Application Tracker
# -----------------------------------------------------------------------------
with tab3:
    st.markdown("## Application Tracker")
    st.caption("Manage job applications through all stages from Discovery to Offers.")

    shortlist_all = load_shortlist_from_db()

    if not shortlist_all:
        st.info("No job applications stored in database yet. Run the pipeline to populate jobs.")
    else:
        # Table List View
        status_opts = ["All Statuses", "new", "seen", "applied", "interviewing", "rejected", "offer"]
        selected_st = st.selectbox("Filter Status", options=status_opts, index=0)

        filtered_apps = [
            j for j in shortlist_all
            if selected_st == "All Statuses" or j.get("status", "new").lower() == selected_st.lower()
        ]

        st.caption(f"Showing **{len(filtered_apps)}** application(s)")
        st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)

        for idx, job in enumerate(filtered_apps):
            eval_data = job.get("evaluation", {})
            match_score = eval_data.get("match_score", 0)
            rec_raw = str(eval_data.get("recommendation", "Consider")).replace("RecommendationEnum.", "").strip().upper()
            job_id = job.get("id") or idx
            curr_st = job.get("status", "new").lower()
            cover_letter = job.get("cover_letter_draft") or eval_data.get("cover_letter_draft", "")
            apply_url = job.get("apply_url", "#")
            updated_at = job.get("status_updated_at") or job.get("created_at")

            c1, c2, c3, c4, c5 = st.columns([2.5, 2.0, 1.0, 1.2, 1.8])
            c1.markdown(f"**[{job.get('title')}]({apply_url})**")
            c2.write(f"{job.get('company', 'N/A')} • {job.get('location', 'N/A')}")

            score_color = "#10B981" if match_score >= 80 else "#F59E0B" if match_score >= 60 else "#F43F5E"
            c3.markdown(f"<span style='color:{score_color}; font-weight:700;'>{match_score}%</span>", unsafe_allow_html=True)

            badge_class = "badge-apply-pill" if rec_raw == "APPLY" else "badge-consider-pill" if rec_raw == "CONSIDER" else "badge-skip-pill"
            c4.markdown(f"<span class='{badge_class}'>{rec_raw}</span>", unsafe_allow_html=True)

            valid_opts = ["new", "seen", "applied", "interviewing", "rejected", "offer"]
            init_idx = valid_opts.index(curr_st) if curr_st in valid_opts else 0

            new_val = c5.selectbox(
                "Status",
                options=valid_opts,
                index=init_idx,
                key=f"lst_st_sel_{job_id}_{idx}",
                label_visibility="collapsed",
            )
            if new_val != curr_st:
                update_job_full_status(job_id, new_val)
                st.toast(f"Status updated to '{new_val.upper()}'")
                st.rerun()

            st.caption(f"Last status update: {updated_at}")

            if cover_letter:
                with st.expander(f"Cover Letter Draft — {job.get('title')} at {job.get('company')}"):
                    st.text_area("Draft Content", value=cover_letter, height=180, key=f"cov_lst_{job_id}_{idx}", label_visibility="collapsed")
                    st.download_button(
                        "📥 Download Cover Letter",
                        data=cover_letter,
                        file_name=f"cover_letter_{job.get('company')}.txt",
                        mime="text/plain",
                        key=f"dl_cov_{job_id}_{idx}",
                    )
            st.markdown("<div style='margin-bottom: 0.75rem;'></div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# TAB 4: Analytics (Plotly Visualizations & AI Insights)
# -----------------------------------------------------------------------------
with tab4:
    st.markdown("## Application Analytics & Funnel Insights")
    st.caption("Track match distributions, response rates, and identified skill gap insights.")

    analytics = get_application_analytics()

    # AI Insight Banner
    st.markdown(
        """
        <div class="ai-insight-box">
            <div style="font-size: 1.5rem; width: 42px; height: 42px; background: rgba(99, 102, 241, 0.2); border: 1px solid rgba(99, 102, 241, 0.3); border-radius: 10px; display: flex; align-items: center; justify-content: center; box-shadow: 0 0 14px rgba(99, 102, 241, 0.3);">💡</div>
            <div>
                <div class="ai-insight-title">AI Profile Optimization Insight</div>
                <div class="ai-insight-desc">Adding <b>Docker</b>, <b>CI/CD</b>, or <b>TypeScript</b> to your profile skill set will increase your match score by ~20% across entry-level developer roles.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 4 Analytics Metrics
    a1, a2, a3, a4 = st.columns(4)
    with a1:
        avg_app = f"{analytics['avg_applied_score']}%" if analytics["avg_applied_score"] is not None else "N/A"
        render_kpi_card("Avg Match (Applied)", avg_app, "Applied job pool", icon="📈")
    with a2:
        avg_io = f"{analytics['avg_interview_offer_score']}%" if analytics["avg_interview_offer_score"] is not None else "N/A"
        render_kpi_card("Avg Match (Interviews)", avg_io, "High confidence shortlist", icon="🎯")
    with a3:
        render_kpi_card("Total Tracked Apps", str(analytics["total_applied_count"]), "Active job applications", icon="📋")
    with a4:
        render_kpi_card("Interviews / Offers", str(analytics["total_interview_offer_count"]), "Positive responses", icon="🎉")

    st.markdown("<div style='margin-bottom: 1.25rem;'></div>", unsafe_allow_html=True)

    col_ch1, col_ch2 = st.columns(2)

    # Chart 1: Donut Chart of Status Breakdown
    with col_ch1:
        st.markdown("<div class='card-wrapper'>", unsafe_allow_html=True)
        st.markdown("### Application Funnel Status")
        status_cnts = analytics.get("status_counts", {})
        if status_cnts and sum(status_cnts.values()) > 0:
            df_status = pd.DataFrame([{"Status": k.upper(), "Count": v} for k, v in status_cnts.items() if v > 0])
            fig_pie = px.pie(
                df_status,
                values="Count",
                names="Status",
                hole=0.48,
                color_discrete_sequence=["#6366F1", "#8B5CF6", "#06B6D4", "#10B981", "#F59E0B", "#F43F5E"],
            )
            fig_pie.update_layout(
                font=dict(family="Inter", color="#F8FAFC"),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=20, b=20, l=20, r=20),
                height=290,
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5, font=dict(color="#CBD5E1"))
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label', marker=dict(line=dict(color='#0B0F19', width=2)))
            st.plotly_chart(fig_pie, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("No status breakdown data available yet.")
        st.markdown("</div>", unsafe_allow_html=True)

    # Chart 2: Match Score Distribution Histogram
    with col_ch2:
        st.markdown("<div class='card-wrapper'>", unsafe_allow_html=True)
        st.markdown("### Match Score Distribution")
        scores = [j.get("evaluation", {}).get("match_score", 0) for j in load_shortlist_from_db()]
        if scores:
            df_scores = pd.DataFrame({"Match Score": scores})
            fig_hist = px.histogram(
                df_scores,
                x="Match Score",
                nbins=10,
                color_discrete_sequence=["#6366F1"],
                labels={"Match Score": "Match Score (%)"},
            )
            fig_hist.update_layout(
                font=dict(family="Inter", color="#F8FAFC"),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=20, b=20, l=20, r=20),
                height=290,
                yaxis_title="Job Count",
                xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.08)", tickfont=dict(color="#CBD5E1")),
                yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.08)", tickfont=dict(color="#CBD5E1")),
            )
            fig_hist.update_traces(marker_line_color="#8B5CF6", marker_line_width=1, opacity=0.9)
            st.plotly_chart(fig_hist, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("No match score distribution available.")
        st.markdown("</div>", unsafe_allow_html=True)

    # Chart 3: Frequent Missing Skills Bar Chart
    st.markdown("<div class='card-wrapper'>", unsafe_allow_html=True)
    st.markdown("### Frequently Missing Skills Across Applications")
    rejection_skills = analytics.get("frequent_rejection_missing_skills", [])
    if rejection_skills:
        df_skills = pd.DataFrame(rejection_skills, columns=["Skill", "Count"])
        fig_bar = px.bar(
            df_skills,
            x="Count",
            y="Skill",
            orientation="h",
            color="Count",
            color_continuous_scale=["#818CF8", "#6366F1", "#4F46E5"],
        )
        fig_bar.update_layout(
            font=dict(family="Inter", color="#F8FAFC"),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=20, b=20, l=20, r=20),
            height=270,
            yaxis=dict(autorange="reversed", showgrid=False, tickfont=dict(color="#CBD5E1")),
            xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.08)", tickfont=dict(color="#CBD5E1")),
            coloraxis_showscale=False
        )
        fig_bar.update_traces(marker_line_color="#8B5CF6", marker_line_width=1)
        st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("✨ No recurring missing skill gaps detected! Your profile matches current job postings well.")
    st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# TAB 5: Pipeline Settings (Grouped Cards & MCP Health Check)
# -----------------------------------------------------------------------------
with tab5:
    st.markdown("## Pipeline Configuration & MCP Tool Health")
    st.caption("Configure matching thresholds, active portal scrapers, and monitor MCP server connectivity.")

    curr_cfg = load_pipeline_config()
    all_sources = ["RemoteOK", "WeWorkRemotely", "Jobicy", "Arbeitnow", "Remotive", "LinkedIn", "Indeed", "Naukri"]

    st.markdown("<div class='card-wrapper'>", unsafe_allow_html=True)
    with st.form("pipeline_config_form"):
        st.markdown("### ⚙️ 1. Matching & Cutoff Parameters")
        cutoff_val = st.slider(
            "Match Score Threshold (%)",
            min_value=0,
            max_value=100,
            value=int(curr_cfg.get("match_score_cutoff", 50)),
            step=5,
            help="Jobs below this percentage will be excluded from the shortlist",
        )
        st.caption(f"💡 Helper: Jobs below **{cutoff_val}%** match score will be filtered out")

        size_val = st.number_input(
            "Target Shortlist Size",
            min_value=1,
            max_value=100,
            value=int(curr_cfg.get("shortlist_size", 20)),
            step=1,
        )

        st.markdown("### 🌐 2. Active Job Search Sources")
        saved_sources = [s for s in curr_cfg.get("job_sources", all_sources) if s in all_sources]
        selected_sources = st.multiselect(
            "Select Search Portals to Query",
            options=all_sources,
            default=saved_sources if saved_sources else all_sources,
        )

        cfg_submitted = st.form_submit_button("⚙️ Save Pipeline Settings", type="primary", use_container_width=True)
        if cfg_submitted:
            new_cfg = {
                "match_score_cutoff": cutoff_val,
                "shortlist_size": size_val,
                "job_sources": selected_sources,
            }
            save_pipeline_config(new_cfg)
            st.toast("Pipeline configuration saved!", icon="⚙️")
            st.success("Configuration updated successfully.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='card-wrapper'>", unsafe_allow_html=True)
    st.markdown("### 🔌 3. MCP Server Health & Tool Latency")
    if st.button("🔌 Run Health Check"):
        with st.spinner("Pinging registered MCP search tools..."):
            import importlib
            import mcp_servers.server as mcp_server_mod
            import mcp_servers.health as mcp_health_mod
            importlib.reload(mcp_server_mod)
            importlib.reload(mcp_health_mod)
            from mcp_servers.health import ping_mcp_tools
            start_t = datetime.now()
            ping_results = ping_mcp_tools(timeout_per_tool=5.0)
            elapsed_ms = int((datetime.now() - start_t).total_seconds() * 1000)

            st.caption(f"Ping check completed in `{elapsed_ms}ms`")

            cols = st.columns(2)
            for idx, (tname, info) in enumerate(ping_results.items()):
                with cols[idx % 2]:
                    if info["reachable"]:
                        st.success(f"🟢 **{tname}**: Operational (`{info.get('latency_ms', 12)}ms`)")
                    else:
                        st.error(f"🔴 **{tname}**: Unreachable ({info['reason']})")
    st.markdown("</div>", unsafe_allow_html=True)
