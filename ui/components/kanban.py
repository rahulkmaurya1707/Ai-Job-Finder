import streamlit as st
from storage.job_storage import update_job_full_status

def render_kanban_board(shortlist_jobs: list):
    """Render a 6-column interactive Kanban board view for application tracking."""
    kanban_statuses = ["new", "seen", "applied", "interviewing", "rejected", "offer"]
    kanban_labels = ["New", "Seen", "Applied", "Interview", "Rejected", "Offer"]
    kanban_colors = {
        "new": "#6366F1",
        "seen": "#94A3B8",
        "applied": "#8B5CF6",
        "interviewing": "#F59E0B",
        "rejected": "#F43F5E",
        "offer": "#10B981"
    }

    cols = st.columns(6)
    for i, st_key in enumerate(kanban_statuses):
        color = kanban_colors[st_key]
        with cols[i]:
            jobs_in_status = [j for j in shortlist_jobs if j.get("status", "new").lower() == st_key]
            st.markdown(
                f"""<div class='kanban-col-header' style='border-top: 3px solid {color};'>
<div style='display: flex; align-items: center; justify-content: space-between;'>
<span style='font-weight: 700; color: #F8FAFC; text-transform: uppercase; font-size: 0.78rem; letter-spacing: 0.04em;'>{kanban_labels[i]}</span>
<span class='kanban-count-pill' style='background-color: {color}25; color: {color}; border: 1px solid {color}44;'>{len(jobs_in_status)}</span>
</div>
</div>""",
                unsafe_allow_html=True,
            )

            for job in jobs_in_status:
                eval_data = job.get("evaluation", {})
                match_score = eval_data.get("match_score", 0)
                job_id = job.get("id")

                st.markdown(
                    f"""<div class="kanban-item-card">
<div class="kanban-item-title">{job.get('title')}</div>
<div class="kanban-item-company">🏢 {job.get('company', 'N/A')}</div>
<div class="kanban-item-score">⚡ {match_score}% Match</div>
</div>""",
                    unsafe_allow_html=True,
                )

                new_st = st.selectbox(
                    "Move Status",
                    options=kanban_statuses,
                    index=kanban_statuses.index(st_key),
                    key=f"kanban_move_{job_id}",
                    label_visibility="collapsed",
                )
                if new_st != st_key:
                    update_job_full_status(job_id, new_st)
                    st.toast(f"Moved '{job.get('title')}' to {new_st.upper()}")
                    st.rerun()
