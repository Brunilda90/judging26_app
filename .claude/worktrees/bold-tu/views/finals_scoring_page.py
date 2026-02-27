"""
views/finals_scoring_page.py

Finals scoring portal — accessible to finals judges.
Light theme, no sidebar. Header: logos | title | user + logout.
Shows the top-5 teams from prelims. Uses separate finals_scores / finals_answers collections.
Score chips replace sliders for a cleaner, choice-based UX.
"""

import os
import base64
import streamlit as st

from db import (
    get_judge_by_id,
    get_questions,
    get_intro_message,
    get_prelim_top5,
    get_team_registrations,
    get_answers_for_judge_competitor_finals,
    save_answers_for_judge_finals,
    get_finals_scores_for_judge,
)

# ── Asset paths ──────────────────────────────────────────────────────────────
_LOGO_AH_PNG   = os.path.join("assets", "autohack_logo.png")
_LOGO_AH_SVG   = os.path.join("assets", "autohack_logo.svg")
_LOGO_GC_PNG   = os.path.join("assets", "georgian_logo.png")

_MEDALS = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]

# Contact info
_CONTACT_SHUBHNEET = "Shubhneet.Sandhu@GeorgianCollege.ca"
_CONTACT_BRUNILDA  = "Brunilda.Xhaferllari@GeorgianCollege.ca"

# ── CSS — identical light theme to scoring_page.py ───────────────────────────
_CSS = """
<style>
/* ── Hide sidebar ── */
section[data-testid="stSidebar"] { display: none !important; }
[data-testid="collapsedControl"]  { display: none !important; }

/* ── Page background ── */
.stApp { background: #ECEEF5 !important; }

/* ── Main content panel ── */
.main .block-container {
    background: #FFFFFF !important;
    border-radius: 16px !important;
    border: 1px solid rgba(0,0,0,0.07) !important;
    padding: 2rem 2.5rem !important;
    max-width: 960px !important;
    margin-top: 1.2rem !important;
    margin-bottom: 2rem !important;
    box-shadow: 0 2px 24px rgba(0,0,0,0.08) !important;
}

/* ── Red-blue accent stripe ── */
.ah-stripe {
    height: 3px;
    background: linear-gradient(90deg, #CC0000 50%, #4A80D4 50%);
    border-radius: 2px;
    width: 100%;
    margin: 0;
}

/* ── Finalist row ── */
.finalist-row {
    display: flex;
    align-items: center;
    padding: 10px 16px;
    border-radius: 10px;
    margin: 5px 0;
    background: #F5F7FD;
    border: 1px solid rgba(74,128,212,0.15);
}
.finalist-rank  { font-size: 1.2rem; width: 2rem; flex-shrink: 0; }
.finalist-name  { flex: 1; font-weight: 700; color: #1A1A2E; font-size: 0.95rem; padding: 0 14px; }
.finalist-prelim {
    background: rgba(74,128,212,0.10);
    border: 1px solid rgba(74,128,212,0.30);
    border-radius: 6px;
    padding: 2px 10px;
    color: #4A80D4;
    font-size: 0.82rem;
    font-weight: 700;
    margin-right: 10px;
}
.finalist-judges { color: #9AA3BC; font-size: 0.78rem; white-space: nowrap; }

/* ── Team info card ── */
.team-info-card {
    background: #F0F5FF;
    border: 1px solid rgba(74,128,212,0.25);
    border-left: 3px solid #4A80D4;
    border-radius: 10px;
    padding: 14px 20px;
    margin: 8px 0 20px;
}
.team-info-name { color: #1A1A2E; font-weight: 700; font-size: 1.05rem; margin: 0 0 3px; }
.team-info-proj { color: #5A6A90; font-size: 0.82rem; font-style: italic; margin: 0 0 10px; }
.team-info-members { color: #3A4A6A; font-size: 0.86rem; line-height: 1.70; margin: 0; }

/* ── Score chip radio buttons ── */
div[data-testid="stRadio"] [role="radiogroup"] {
    display: flex !important;
    flex-wrap: wrap !important;
    gap: 6px !important;
    margin-top: 4px !important;
}
div[data-testid="stRadio"] [role="radiogroup"] > label {
    border: 2px solid #D8DCF0 !important;
    border-radius: 8px !important;
    min-width: 44px !important;
    height: 44px !important;
    padding: 0 10px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-weight: 700 !important;
    font-size: 0.92rem !important;
    background: #F5F7FD !important;
    cursor: pointer !important;
    transition: all 0.15s ease !important;
    color: #3A4060 !important;
}
div[data-testid="stRadio"] [role="radiogroup"] > label:hover {
    border-color: #CC0000 !important;
    background: #FFF5F5 !important;
    color: #CC0000 !important;
}
div[data-testid="stRadio"] [role="radiogroup"] > label > div:first-child {
    display: none !important;
}
div[data-testid="stRadio"] [role="radiogroup"] > label:has(input:checked) {
    background: #CC0000 !important;
    border-color: #CC0000 !important;
    color: #FFFFFF !important;
}

/* ── Primary button → AutoHack red ── */
[data-testid="stButton"] button[kind="primary"],
[data-testid="stBaseButton-primary"] {
    background-color: #CC0000 !important;
    border-color: #CC0000 !important;
    color: #FFFFFF !important;
}
[data-testid="stButton"] button[kind="primary"]:hover,
[data-testid="stBaseButton-primary"]:hover {
    background-color: #AA0000 !important;
    border-color: #AA0000 !important;
}

/* ── Metric cards ── */
[data-testid="stMetric"] {
    background: #F5F7FD !important;
    border: 1px solid rgba(74,128,212,0.18) !important;
    border-radius: 10px !important;
    padding: 12px 16px !important;
}
[data-testid="stMetricLabel"] { color: #5A6A90 !important; font-size: 0.78rem !important; }
[data-testid="stMetricValue"] { color: #1A1A2E !important; font-size: 1.5rem !important; font-weight: 700 !important; }
</style>
"""


# ── Asset helpers ─────────────────────────────────────────────────────────────

def _b64_tag(path: str, style: str, alt: str = "") -> str:
    if not os.path.exists(path):
        return ""
    ext  = os.path.splitext(path)[1].lstrip(".").lower()
    mime = "image/svg+xml" if ext == "svg" else f"image/{ext}"
    with open(path, "rb") as fh:
        b64 = base64.b64encode(fh.read()).decode()
    return f'<img src="data:{mime};base64,{b64}" style="{style}" alt="{alt}">'


def _render_header(title: str, username: str, logout_key: str = "finals_signout"):
    """Three-column header: logos | title | signed-in info + Log Out button."""
    gc_tag = _b64_tag(
        _LOGO_GC_PNG,
        "height:40px;object-fit:contain;vertical-align:middle;",
        "Georgian College",
    )
    ah_tag = (
        _b64_tag(_LOGO_AH_PNG,
                 "height:36px;object-fit:contain;vertical-align:middle;",
                 "AutoHack 2026")
        or _b64_tag(_LOGO_AH_SVG,
                    "height:36px;object-fit:contain;vertical-align:middle;",
                    "AutoHack 2026")
    )
    logos_html = (
        '<div style="display:flex;align-items:center;gap:10px;padding-top:2px;">'
        + gc_tag
        + (
            '<span style="color:#D0D5E8;font-size:1.1rem;font-weight:300;">×</span>'
            + ah_tag
            if ah_tag else ""
        )
        + '</div>'
    )

    col_logo, col_title, col_user = st.columns([3, 4, 3])

    with col_logo:
        st.markdown(logos_html, unsafe_allow_html=True)

    with col_title:
        st.markdown(
            f'<div style="text-align:center;">'
            f'<p style="margin:0;font-size:1.35rem;font-weight:800;'
            f'letter-spacing:3px;text-transform:uppercase;color:#1A1A2E;">'
            f'{title}</p>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with col_user:
        st.markdown(
            f'<p style="text-align:right;color:#8A94B0;font-size:0.82rem;'
            f'margin:0 0 5px;">Signed in as <strong style="color:#3A4060;">'
            f'{username}</strong></p>',
            unsafe_allow_html=True,
        )
        if st.button("Log Out", key=logout_key, type="primary", use_container_width=True):
            st.session_state.pop("user", None)
            st.rerun()

    st.markdown('<div class="ah-stripe" style="margin-top:8px;"></div>', unsafe_allow_html=True)


def _render_top5_table(top5: list):
    rows_html = ""
    for i, team in enumerate(top5):
        medal     = _MEDALS[i] if i < len(_MEDALS) else f"{i+1}."
        score_str = f"{team['avg_score'] / 10:.1f}" if team.get("avg_score") else "—"
        judges    = team.get("num_scores", 0)
        rows_html += (
            f'<div class="finalist-row">'
            f'  <span class="finalist-rank">{medal}</span>'
            f'  <span class="finalist-name">{team["competitor_name"]}</span>'
            f'  <span class="finalist-prelim">Prelim avg {score_str}/10</span>'
            f'  <span class="finalist-judges">{judges} judge{"s" if judges != 1 else ""}</span>'
            f'</div>'
        )
    st.markdown(rows_html, unsafe_allow_html=True)


def _render_team_card(team_name: str, registrations: list):
    reg = next((r for r in registrations if r["team_name"] == team_name), None)
    if not reg:
        return
    project = reg.get("project_name", "")
    members = reg.get("members", [])
    member_lines = "".join(
        f"&nbsp;&nbsp;{i}. {m.get('name', '?')} "
        f"<span style='color:#8A94B0;font-size:0.79rem;'>"
        f"({m.get('institution', '') or m.get('program', '') or ''})</span><br>"
        for i, m in enumerate(members, 1)
    )
    count = len(members)
    st.markdown(
        f'<div class="team-info-card">'
        f'  <p class="team-info-name">👥 {team_name}</p>'
        + (f'  <p class="team-info-proj">📐 {project}</p>' if project else "")
        + f'  <p class="team-info-members">'
        f'    <strong>{count} member{"s" if count != 1 else ""}</strong><br>'
        f'    {member_lines}'
        f'  </p>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _score_label(v: int) -> str:
    if v == 0:  return "Not scored"
    if v <= 2:  return f"{v} · Poor"
    if v <= 4:  return f"{v} · Below Average"
    if v == 5:  return f"{v} · Average"
    if v <= 7:  return f"{v} · Good"
    if v <= 9:  return f"{v} · Excellent"
    return f"{v} · Outstanding"


def _render_scoring_form(judge_id, comp_id: str, comp_name: str, questions, view_only: bool):
    """Radio chip (0–10) scoring form for a finalist team."""
    existing = (
        get_answers_for_judge_competitor_finals(judge_id, comp_id)
        if judge_id else {}
    )
    scored      = any(int(v) > 0 for v in existing.values()) if existing else False
    editing_key = f"finals_editing_{judge_id}_{comp_id}"
    editing     = st.session_state.get(editing_key, False) if not view_only else False

    if not view_only:
        if scored and not editing:
            st.success(f"✅ Finals scores submitted for **{comp_name}**.")
            if st.button("✏️ Edit Scores", key=f"finals_edit_{comp_id}"):
                st.session_state[editing_key] = True
                st.rerun()
        if editing:
            if st.button("✕ Cancel Edit", key=f"finals_cancel_{comp_id}"):
                st.session_state[editing_key] = False
                st.rerun()

    st.caption(
        "Score each criterion: **0** = Not Scored · **1–3** = Needs Work · "
        "**4–6** = Meets Expectations · **7–8** = Good · **9–10** = Outstanding"
    )

    answers = {}
    for q in questions:
        stored_raw    = int(existing.get(q["id"], 0))
        stored_choice = int(stored_raw / 10) if stored_raw else 0
        choice = st.radio(
            q["prompt"],
            options=list(range(0, 11)),
            index=stored_choice,
            horizontal=True,
            format_func=lambda x: "—" if x == 0 else str(x),
            key=f"finals_q_{judge_id}_{comp_id}_{q['id']}",
            disabled=view_only or (scored and not editing),
        )
        answers[q["id"]] = choice
        st.caption(f"→ {_score_label(choice)}")

    if not view_only and not (scored and not editing):
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🏆 Save Finals Scores", key=f"finals_save_{comp_id}", type="primary"):
            missing = [q for q in questions if answers.get(q["id"], 0) == 0]
            if missing:
                st.error(
                    f"Please score all {len(missing)} remaining "
                    f"question{'s' if len(missing) != 1 else ''} before saving."
                )
            else:
                cleaned = {qid: val * 10 for qid, val in answers.items()}
                save_answers_for_judge_finals(judge_id, comp_id, cleaned)
                st.session_state[editing_key] = False
                st.session_state["finals_score_saved"] = True
                st.rerun()


# ── Main entry point ──────────────────────────────────────────────────────────

def show():
    user     = st.session_state.get("user")
    is_judge = user and user.get("role") == "judge"

    if not is_judge:
        st.error("Judge access required.")
        st.stop()

    if user.get("judge_round", "prelims") != "finals":
        st.error("⛔ This page is for Finals judges only.")
        st.stop()

    # ── Apply CSS ─────────────────────────────────────────────────────────────
    st.markdown(_CSS, unsafe_allow_html=True)

    # ── Header ───────────────────────────────────────────────────────────────
    username = user.get("username", "judge")
    _render_header("Finals Scoring", username)

    # Finals badge (right-aligned, below header)
    st.markdown(
        '<p style="text-align:right;color:#8A94B0;font-size:0.85rem;margin:6px 0 0;">'
        '🏆 <strong style="color:#CC0000;">Finals Judge</strong></p>',
        unsafe_allow_html=True,
    )

    st.markdown('<hr style="border-color:rgba(0,0,0,0.08);margin:14px 0 18px;">', unsafe_allow_html=True)

    if st.session_state.pop("finals_score_saved", False):
        st.toast("Finals scores saved!", icon="🏆")

    # ── Intro message (always shown) ──────────────────────────────────────────
    intro = get_intro_message()
    if intro:
        st.info(intro)

    # ── Contact info (always shown) ───────────────────────────────────────────
    st.caption(
        f"If you have any questions or face any issues, please contact "
        f"**Shubhneet Sandhu** — [{_CONTACT_SHUBHNEET}](mailto:{_CONTACT_SHUBHNEET}) "
        f"or **Brunilda** — [{_CONTACT_BRUNILDA}](mailto:{_CONTACT_BRUNILDA})"
    )

    # ── Load scoring questions ────────────────────────────────────────────────
    questions = get_questions()
    if not questions:
        st.warning("Admin needs to add scoring questions first.")
        return

    judge_id = user.get("judge_id")

    # ── Top-5 from prelims ────────────────────────────────────────────────────
    top5 = get_prelim_top5()
    if not top5:
        st.info(
            "🏁 No prelims scores have been entered yet. "
            "The top-5 finalist teams will appear here once prelims scoring is complete."
        )
        return

    # ── Metrics ───────────────────────────────────────────────────────────────
    finals_scores_map   = get_finals_scores_for_judge(judge_id) if judge_id else {}
    top5_ids            = {t["competitor_id"] for t in top5}
    finals_scored_count = sum(
        1 for cid in top5_ids
        if cid in finals_scores_map and finals_scores_map[cid] > 0
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("Finalist Teams", len(top5))
    c2.metric("Scored",         finals_scored_count)
    c3.metric("Remaining",      len(top5) - finals_scored_count)

    st.markdown('<hr style="border-color:rgba(0,0,0,0.08);margin:12px 0 16px;">', unsafe_allow_html=True)

    st.markdown(
        '<p style="color:#3A4060;font-size:0.95rem;font-weight:600;margin:0 0 10px;">'
        '🏆 Finalist Teams (from Prelims)</p>',
        unsafe_allow_html=True,
    )
    _render_top5_table(top5)

    st.markdown('<hr style="border-color:rgba(0,0,0,0.08);margin:16px 0 16px;">', unsafe_allow_html=True)

    # Load registrations for member lookups
    all_registrations = get_team_registrations()

    # ── Team selector ─────────────────────────────────────────────────────────
    option_labels = []
    comp_by_label = {}
    for team in top5:
        cid       = team["competitor_id"]
        is_scored = cid in finals_scores_map and finals_scores_map[cid] > 0
        label     = f"{'✅' if is_scored else '⏳'}  {team['competitor_name']}"
        option_labels.append(label)
        comp_by_label[label] = team

    selected_label = st.selectbox("Select a finalist team to score", option_labels)
    selected_team  = comp_by_label[selected_label]
    comp_id        = selected_team["competitor_id"]
    comp_name      = selected_team["competitor_name"]

    _render_team_card(comp_name, all_registrations)

    st.markdown('<hr style="border-color:rgba(0,0,0,0.08);margin:4px 0 18px;">', unsafe_allow_html=True)

    _render_scoring_form(judge_id, comp_id, comp_name, questions, view_only=False)
