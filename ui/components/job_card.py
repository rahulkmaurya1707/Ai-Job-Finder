import streamlit as st
from storage.job_storage import update_shortlist_job_status

def is_senior_role(title: str) -> bool:
    """Check if job title indicates a senior or lead position."""
    senior_keywords = ["senior", "sr.", "sr ", "lead", "principal", "architect", "staff", "manager", "head"]
    t_lower = title.lower()
    return any(kw in t_lower for kw in senior_keywords)

def render_job_card(job: dict, idx: int):
    """Render a modern SaaS job card with circular score ring, stretch badges, skill chips, and actions inside one container."""
    eval_data = job.get("evaluation", {})
    match_score = eval_data.get("match_score", 0)
    rec_raw = str(eval_data.get("recommendation", "Consider")).replace("RecommendationEnum.", "").strip().upper()
    matching_skills = eval_data.get("matching_skills", [])
    missing_skills = eval_data.get("missing_skills", [])
    reasoning = eval_data.get("one_line_reasoning", "")
    apply_url = job.get("apply_url", "#")
    job_id = job.get("id")
    title = job.get("title", "Software Engineer")
    company = job.get("company", "N/A")
    company_initial = company[0].upper() if company and company != "N/A" and company[0].isalpha() else "🏢"

    badge_class = "badge-apply-pill" if rec_raw == "APPLY" else "badge-consider-pill" if rec_raw == "CONSIDER" else "badge-skip-pill"
    badge_label = f"🟢 {rec_raw}" if rec_raw == "APPLY" else f"🟡 {rec_raw}" if rec_raw == "CONSIDER" else f"⚪ {rec_raw}"

    score_color = "#10B981" if match_score >= 80 else "#F59E0B" if match_score >= 60 else "#F43F5E"
    dashoffset = int(113 - (min(match_score, 100) / 100.0) * 113)

    is_stretch = is_senior_role(title)
    stretch_badge = '<span class="badge-consider-pill" style="margin-left:0.4rem; background:rgba(245,158,11,0.15); color:#F59E0B; border:1px solid rgba(245,158,11,0.3);">⚠️ Stretch Role</span>' if is_stretch else ""

    # Build skill chips HTML (top 3 matching + top 2 missing)
    skill_chips_html = ""
    for sk in matching_skills[:3]:
        skill_chips_html += f"<span class='skill-chip-match'>✅ {sk}</span>"
    for sk in missing_skills[:2]:
        skill_chips_html += f"<span class='skill-chip-miss'>⚠️ {sk}</span>"

    is_applied_init = job.get("is_applied", False)
    is_seen_init = job.get("is_seen", False)

    card_header_html = f"""<div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; margin-bottom: 0.75rem;">
<div style="display: flex; gap: 1rem; align-items: flex-start; flex: 1;">
<div class="company-avatar-box">{company_initial}</div>
<div>
<div class="job-card-title"><a href="{apply_url}" target="_blank">{title}</a></div>
<div class="job-meta-line">
<span>🏢 <b style="color:#F8FAFC;">{company}</b></span>
<span>•</span>
<span>📍 {job.get('location', 'N/A')}</span>
<span class="badge-remote-pill">Remote</span>
<span class="badge-source-pill">{job.get('source', 'Unknown')}</span>
<span class="{badge_class}">{badge_label}</span>
{stretch_badge}
</div>
<div style="margin-top: 0.65rem;">
{skill_chips_html}
</div>
</div>
</div>
<div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding-left: 0.75rem;">
<svg width="56" height="56" viewBox="0 0 44 44">
<circle cx="22" cy="22" r="18" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="3.5" />
<circle cx="22" cy="22" r="18" fill="none" stroke="{score_color}" stroke-width="3.5" stroke-dasharray="113" stroke-dashoffset="{dashoffset}" stroke-linecap="round" transform="rotate(-90 22 22)" />
<text x="22" y="26" text-anchor="middle" font-size="11" font-weight="800" fill="{score_color}">{match_score}%</text>
</svg>
</div>
</div>"""

    # All Card Contents Wrapped in Single Bordered Container
    with st.container(border=True):
        st.markdown(card_header_html, unsafe_allow_html=True)

        col_act1, col_act2, col_act3 = st.columns([1.4, 1.0, 1.0], vertical_alignment="center")

        with col_act1:
            st.link_button("Apply Now ↗", apply_url, type="primary", use_container_width=True)

        seen_checked = col_act2.checkbox("Seen", value=is_seen_init, key=f"seen_chk_{job_id}_{idx}")
        applied_checked = col_act3.checkbox("Applied", value=is_applied_init, key=f"applied_chk_{job_id}_{idx}")

        if seen_checked != is_seen_init:
            update_shortlist_job_status(job_id, is_seen=seen_checked)
            st.rerun()
        if applied_checked != is_applied_init:
            update_shortlist_job_status(job_id, is_applied=applied_checked)
            st.rerun()

        # Skill Breakdown & Cover Letter Expander
        with st.expander(f"🔍 Skill Breakdown & Cover Letter — {title} ({company})"):
            st.markdown(f"**AI Evaluation Reasoning:** {reasoning}")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Matched Skills:**")
                if matching_skills:
                    chips_html = "".join([f"<span class='skill-chip-match'>✅ {sk}</span>" for sk in matching_skills])
                    st.markdown(chips_html, unsafe_allow_html=True)
                else:
                    st.caption("None identified")
            with c2:
                st.markdown("**Missing Skills:**")
                if missing_skills:
                    chips_html = "".join([f"<span class='skill-chip-miss'>⚠️ {sk}</span>" for sk in missing_skills])
                    st.markdown(chips_html, unsafe_allow_html=True)
                else:
                    st.caption("None identified")

            cover_letter = job.get("cover_letter_draft") or eval_data.get("cover_letter_draft", "")
            if cover_letter:
                st.markdown("---")
                st.markdown("**Cover Letter Draft:**")
                st.text_area("Cover Letter", value=cover_letter, height=180, key=f"cov_area_{job_id}_{idx}", label_visibility="collapsed")

    st.markdown("<div style='margin-bottom: 1.25rem;'></div>", unsafe_allow_html=True)

