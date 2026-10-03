import streamlit as st

def render_kpi_card(title: str, value: str, subtext: str = "", icon: str = "📊", accent_color: str = "#6366F1"):
    """Render a clean, modern KPI metric card with distinct accent color and larger badge."""
    subtext_html = f'<div class="kpi-card-subtext"><span>•</span> {subtext}</div>' if subtext else ""
    card_html = f"""<div class="kpi-card-box" style="border-top: 3px solid {accent_color};">
<div class="kpi-card-label">
<span class="kpi-card-icon-badge" style="background-color: {accent_color}22; border-color: {accent_color}44;">{icon}</span>
<span>{title}</span>
</div>
<div class="kpi-card-number">{value}</div>
{subtext_html}
</div>"""
    st.markdown(card_html, unsafe_allow_html=True)
