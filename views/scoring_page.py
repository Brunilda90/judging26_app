"""
views/scoring_page.py

Prelims scoring portal — accessible to prelims judges.
Design mirrors booking_page.py / registration_page.py exactly:
  • Grey tire-track background with light glassmorphism panel
  • Same centered dark pill banner: large AH white logo + GC logo pinned bottom-right
  • Same .ah-section brand labels + ah-subtitle / ah-stripe below banner
  • Score chips (0–10 horizontal radio) on question cards
"""

import os
import base64
import streamlit as st

from db import (
    get_or_create_competitor_for_team,
    get_judge_by_id,
    get_questions,
    get_intro_message,
    get_answers_for_judge_competitor,
    save_answers_for_judge,
    get_teams_booked_in_room,
    get_scores_for_judge_all,
    get_prelim_comments_for_judge_competitor,
)

# ── Asset paths ────────────────────────────────────────────────────────────────
_LOGO_AH_WHITE = os.path.join("assets", "autohack_logo_white.png")
_LOGO_AH_PNG   = os.path.join("assets", "autohack_logo.png")
_LOGO_AH_SVG   = os.path.join("assets", "autohack_logo.svg")
_LOGO_GC_PNG   = os.path.join("assets", "georgian_logo.png")
_BG_URL = (
    "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7"
    "?auto=format&fit=crop&w=1920&q=80"
)

_CONTACT_SHUBHNEET = "Shubhneet.Sandhu@GeorgianCollege.ca"
_CONTACT_BRUNILDA  = "Brunilda.Xhaferllari@GeorgianCollege.ca"


# ── Asset helpers ──────────────────────────────────────────────────────────────

@st.cache_data
def _b64_tag(path: str, style: str, alt: str = "") -> str:
    """Return an <img> tag with the image embedded as a base64 data URI."""
    if not os.path.exists(path):
        return ""
    ext  = os.path.splitext(path)[1].lstrip(".").lower()
    mime = "image/svg+xml" if ext == "svg" else f"image/{ext}"
    with open(path, "rb") as fh:
        b64 = base64.b64encode(fh.read()).decode()
    return f'<img src="data:{mime};base64,{b64}" style="{style}" alt="{alt}">'


# ── CSS (dark theme, consistent with home / booking / scheduling pages) ────────

_CSS = f"""
<style>
/* ── Hide Streamlit sidebar ── */
section[data-testid="stSidebar"] {{ display: none !important; }}
[data-testid="collapsedControl"]  {{ display: none !important; }}

/* ── Page background: dark automotive photo ── */
.stApp {{
    background-image:
        linear-gradient(rgba(0,0,0,0.80), rgba(0,0,0,0.86)),
        url('{_BG_URL}');
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
    min-height: 100vh;
}}

/* ── Outer app container top padding ── */
[data-testid="stAppViewBlockContainer"] {{
    padding: 1rem 1rem 10rem !important;
}}

/* ── Main panel: dark glassmorphism ── */
.main .block-container {{
    background: rgba(10, 12, 22, 0.68) !important;
    backdrop-filter: blur(18px) !important;
    -webkit-backdrop-filter: blur(18px) !important;
    border-radius: 0 0 20px 20px !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    padding: 0 3rem 2rem !important;
    max-width: 980px !important;
    margin-top: 0.3rem !important;
    margin-bottom: 2rem !important;
    box-shadow: 0 8px 60px rgba(0,0,0,0.60) !important;
}}
/* Pull navbar flush to the top of the panel */
.main .block-container > div:first-child {{
    margin-top: -3.5rem !important;
}}

/* ── Navbar sub-row: vertically centre "Signed in as" with logout button ── */
[data-testid="stHorizontalBlock"]:first-of-type [data-testid="stHorizontalBlock"] {{
    align-items: center !important;
}}
[data-testid="stHorizontalBlock"]:first-of-type [data-testid="stHorizontalBlock"]
    [data-testid="stMarkdownContainer"] {{
    display: flex !important;
    align-items: center !important;
    justify-content: flex-end !important;
}}

/* ── Brand section labels ── */
.ah-section {{
    color: #FF4040; font-weight: 700; font-size: 0.80rem;
    text-transform: uppercase; letter-spacing: 1.4px;
    border-left: 3px solid #CC0000; padding: 2px 0 2px 10px; margin: 6px 0 12px;
}}

/* ── Subtitle + stripe below banner ── */
.ah-subtitle {{
    color: rgba(200,210,230,0.70); font-size: 0.95rem;
    letter-spacing: 2.5px; text-transform: uppercase; font-weight: 300; margin: 0;
}}
.ah-stripe {{
    height: 3px;
    background: linear-gradient(90deg, #CC0000 50%, #4A80D4 50%);
    border-radius: 2px; width: 55%; margin: 16px auto 0;
}}

/* ── Info card (dark) ── */
.ah-info-card {{
    background: rgba(15, 20, 48, 0.72);
    border: 1px solid rgba(74,128,212,0.30);
    border-radius: 12px; padding: 16px 20px; margin-bottom: 12px;
}}
.ah-info-card p {{ color: rgba(215,228,255,0.88) !important; margin: 4px 0 !important; }}
.ah-info-label {{
    color: rgba(107,159,228,0.85) !important; font-weight: 600 !important;
    font-size: 0.82rem !important; text-transform: uppercase; letter-spacing: 0.8px;
}}

/* ── Top navbar user text ── */
.ah-nav-user {{
    font-size: 13px; color: rgba(160,180,220,0.70);
    margin: 0; line-height: 1.45; text-align: right;
}}
.ah-nav-user strong {{ color: rgba(220,232,255,0.92); font-size: 0.90rem; }}

/* ── Navbar row: vertically center logos and right-side content ── */
[data-testid="stHorizontalBlock"]:first-of-type {{
    align-items: center !important;
}}
/* ── Logout button ── */
[data-testid="stHorizontalBlock"]:first-of-type [data-testid="stBaseButton-primary"] {{
    font-size: 0.55em !important;
    padding: 0.2rem 0.65rem !important;
    text-transform: none !important;
    white-space: nowrap !important;
}}

/* ── Pull subtitle heading up closer to navbar ── */
[data-testid="stHorizontalBlock"]:first-of-type + div {{
    margin-top: -2rem !important;
}}

/* ── Round / room badges ── */
.round-pill {{
    display: inline-block;
    background: rgba(204,0,0,0.15);
    border: 1px solid rgba(204,0,0,0.40);
    color: rgba(255,160,160,0.90);
    font-size: 0.82rem; font-weight: 700;
    padding: 6px 16px; border-radius: 20px; letter-spacing: 0.5px;
}}
.room-tag {{
    display: inline-flex; align-items: center; gap: 8px;
    background: rgba(74,128,212,0.14);
    border: 1px solid rgba(74,128,212,0.35);
    border-radius: 8px; padding: 6px 16px;
    font-size: 0.87rem; color: rgba(200,215,245,0.80); font-weight: 500;
}}
.room-tag strong {{ color: #FFFFFF; font-weight: 800; }}

/* ── Body text ── */
.stMarkdown p, .stMarkdown li, .stMarkdown strong, .stMarkdown em {{
    color: rgba(225,230,245,0.90) !important;
}}
label, .stRadio label {{ color: rgba(200,215,245,0.80) !important; }}

/* ── Inputs: dark bg, white text ── */
[data-baseweb="base-input"], [data-baseweb="textarea"] {{
    background: rgba(18,20,40,0.92) !important;
    border: 1px solid rgba(255,255,255,0.16) !important;
    border-radius: 8px !important;
}}
[data-baseweb="base-input"] input, [data-baseweb="textarea"] textarea {{
    background: transparent !important;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
}}
[data-baseweb="textarea"] textarea::placeholder {{
    color: rgba(160,175,200,0.50) !important;
    -webkit-text-fill-color: rgba(160,175,200,0.50) !important;
}}

/* ── Divider ── */
hr {{ border-color: rgba(255,255,255,0.10) !important; margin: 18px 0 !important; }}

/* ── Metric cards ── */
[data-testid="stMetric"] {{
    background: rgba(15,18,40,0.50) !important;
    border: 1px solid rgba(74,128,212,0.25) !important;
    border-radius: 12px !important;
    padding: 12px 16px !important;
}}
[data-testid="stMetricLabel"] {{
    color: rgba(180,200,235,0.75) !important; font-size: 0.78rem !important;
    text-transform: uppercase !important; letter-spacing: 0.9px !important; font-weight: 600 !important;
}}
[data-testid="stMetricValue"] {{
    color: #FFFFFF !important; font-size: 1.6rem !important; font-weight: 700 !important;
}}

/* ── Full team info card ── */
.team-info-card {{
    background: rgba(15,20,48,0.72);
    border: 1px solid rgba(74,128,212,0.30);
    border-left: 5px solid #4A80D4;
    border-radius: 14px; padding: 18px 22px; margin: 6px 0 20px;
    box-shadow: 0 3px 14px rgba(0,0,0,0.30);
}}
.team-info-name {{ color: #FFFFFF; font-weight: 800; font-size: 1.10rem; margin: 0 0 4px; }}
.team-info-proj {{ color: rgba(180,200,235,0.65); font-size: 0.83rem; font-style: italic; margin: 0 0 14px; }}
.team-info-members {{ color: rgba(200,215,245,0.80); font-size: 0.87rem; line-height: 1.80; margin: 0; }}

/* ── Question card header (blue accent for prelims) ── */
.q-header {{
    background: rgba(15,22,50,0.80);
    border: 1px solid rgba(74,128,212,0.28);
    border-left: 4px solid #4A80D4;
    border-bottom: none;
    border-radius: 12px 12px 0 0;
    padding: 13px 18px 11px;
    display: flex; align-items: center; gap: 12px;
    margin-top: 18px;
}}
.q-num {{
    background: #4A80D4; color: #FFFFFF;
    font-size: 0.68rem; font-weight: 800;
    padding: 3px 9px; border-radius: 5px;
    letter-spacing: 0.8px; text-transform: uppercase;
    flex-shrink: 0; white-space: nowrap;
    box-shadow: 0 1px 4px rgba(74,128,212,0.30);
}}
.q-text {{ font-size: 0.96rem; font-weight: 600; color: rgba(225,235,255,0.95); line-height: 1.45; margin: 0; }}

/* ── Score chip radio buttons ── */
div[data-testid="stRadio"] {{
    background: rgba(12,15,30,0.70);
    border: 1px solid rgba(74,128,212,0.22);
    border-top: none;
    border-radius: 0 0 12px 12px;
    padding: 14px 18px;
    margin-bottom: 4px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.30);
}}
div[data-testid="stRadio"] label[data-testid="stWidgetLabel"] {{ display: none !important; }}
div[data-testid="stRadio"] [role="radiogroup"] {{
    display: flex !important; flex-wrap: wrap !important;
    gap: 7px !important; margin: 0 !important;
}}
div[data-testid="stRadio"] [role="radiogroup"] > label {{
    border: 2px solid rgba(74,128,212,0.40) !important;
    border-radius: 9px !important;
    min-width: 48px !important; height: 48px !important;
    padding: 0 8px !important;
    display: flex !important; align-items: center !important; justify-content: center !important;
    font-weight: 700 !important; font-size: 0.93rem !important;
    background: rgba(18,22,45,0.85) !important;
    cursor: pointer !important;
    transition: all 0.13s cubic-bezier(0.4,0,0.2,1) !important;
    color: rgba(190,205,225,0.65) !important; user-select: none !important;
}}
div[data-testid="stRadio"] [role="radiogroup"] > label:hover {{
    border-color: #CC0000 !important;
    background: rgba(204,0,0,0.12) !important;
    color: rgba(255,160,160,0.95) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 12px rgba(204,0,0,0.25) !important;
}}
div[data-testid="stRadio"] [role="radiogroup"] > label > div:first-child {{ display: none !important; }}
div[data-testid="stRadio"] [role="radiogroup"] > label p {{
    color: rgba(190,205,225,0.65) !important;
}}
div[data-testid="stRadio"] [role="radiogroup"] > label:has(input:checked) {{
    background: linear-gradient(135deg, #CC0000, #A80000) !important;
    border-color: #CC0000 !important; color: #FFFFFF !important;
    box-shadow: 0 4px 16px rgba(204,0,0,0.45) !important;
    transform: translateY(-2px) !important;
}}
div[data-testid="stRadio"] [role="radiogroup"] > label:has(input:checked) p {{
    color: #FFFFFF !important;
}}

/* ── Score result cap ── */
.score-result {{
    font-size: 0.79rem; color: rgba(160,180,220,0.75);
    padding: 8px 18px 12px;
    border: 1px solid rgba(74,128,212,0.18); border-top: none;
    border-radius: 0 0 12px 12px;
    background: rgba(12,15,30,0.55); margin-top: -4px; margin-bottom: 2px;
    font-style: italic;
}}

/* ── Alert boxes ── */
[data-testid="stInfo"] {{
    background: rgba(15,25,55,0.70) !important;
    border: 1px solid rgba(74,128,212,0.30) !important;
    border-left: 4px solid #4A80D4 !important;
    border-radius: 12px !important; color: rgba(200,215,245,0.90) !important;
}}
[data-testid="stSuccess"] {{ border-radius: 10px !important; border-left: 4px solid #1a9e5c !important; }}
[data-testid="stWarning"] {{ border-radius: 10px !important; border-left: 4px solid #E08000 !important; }}
[data-testid="stError"]   {{ border-radius: 10px !important; border-left: 4px solid #CC0000 !important; }}

/* ── Primary button ── */
[data-testid="stBaseButton-primary"] {{
    background-color: #CC0000 !important; border-color: #CC0000 !important;
    color: white !important; font-weight: 700 !important; font-size: 0.95rem !important;
    letter-spacing: 0.8px !important; border-radius: 8px !important;
    text-transform: uppercase !important;
    box-shadow: 0 4px 24px rgba(204,0,0,0.45) !important;
}}
[data-testid="stBaseButton-primary"]:hover {{
    background-color: #EE1111 !important; border-color: #EE1111 !important;
    box-shadow: 0 6px 32px rgba(204,0,0,0.65) !important;
    transform: translateY(-1px) !important;
}}

/* ── Selectbox label ── */
[data-testid="stSelectbox"] label {{
    color: rgba(200,215,245,0.80) !important; font-weight: 600 !important;
    font-size: 0.86rem !important; text-transform: uppercase !important;
    letter-spacing: 0.6px !important;
}}

/* ── Caption ── */
.stCaption p {{ color: rgba(150,165,195,0.70) !important; font-size: 0.80rem !important; }}
</style>
"""


# ── Render helpers ─────────────────────────────────────────────────────────────

def _render_css():
    """Inject page CSS (navbar + content styles)."""
    st.markdown(_CSS, unsafe_allow_html=True)


def _render_team_card(team_info: dict):
    """Light-themed team details card using .ah-info-card style."""
    name    = team_info.get("team_name", "Unknown Team")
    project = team_info.get("project_name", "")
    members = team_info.get("members", [])
    count   = len(members)

    member_lines = "".join(
        f'<p style="margin:3px 0;color:rgba(215,228,255,0.85);font-size:0.88rem;">'
        f'• <strong style="color:#FFFFFF;">{m.get("name","—")}</strong>'
        + (
            f'&nbsp;&nbsp;<span style="color:rgba(150,170,210,0.70);font-size:0.82rem;">'
            f'{m.get("institution","")}{"  ·  " + m.get("program","") if m.get("program") else ""}'
            f'</span>'
            if m.get("institution") or m.get("program") else ""
        )
        + f'</p>'
        for m in members
    )

    st.markdown(
        f'<div class="ah-info-card">'
        f'  <p class="ah-info-label">Team Name</p>'
        f'  <p style="font-size:1.1rem;font-weight:700;color:#FFFFFF;margin:0 0 10px;">{name}</p>'
        + (
            f'  <p class="ah-info-label">Project</p>'
            f'  <p style="margin:0 0 10px;color:rgba(215,228,255,0.80);">{project}</p>'
            if project else ""
        )
        + f'  <p class="ah-info-label">Members ({count})</p>'
        f'  {member_lines}'
        f'</div>',
        unsafe_allow_html=True,
    )


def _score_label(v: int) -> str:
    if v == 0:  return "Not yet scored"
    if v == 1:  return "1 · Needs significant improvement"
    if v <= 3:  return f"{v} · Needs work"
    if v <= 5:  return f"{v} · Meets expectations"
    if v <= 7:  return f"{v} · Good"
    if v <= 9:  return f"{v} · Excellent"
    return "10 · Outstanding 🌟"


def _render_scoring_form(judge_id, comp_id: str, comp_name: str, questions, view_only: bool):
    """Question cards with score chip radios (0–10).
    Wrapped in st.form when editable so the page only reruns on Save Scores,
    not on every chip click."""
    import contextlib

    existing = (
        get_answers_for_judge_competitor(judge_id, comp_id)
        if judge_id else {}
    )
    scored      = any(int(v) > 0 for v in existing.values()) if existing else False
    editing_key = f"prelims_editing_{judge_id}_{comp_id}"
    editing     = st.session_state.get(editing_key, False) if not view_only else False
    existing_comments = get_prelim_comments_for_judge_competitor(judge_id, comp_id) if judge_id else ""

    if not view_only:
        if scored and not editing:
            st.success("✅ Scores saved for this team. Use **Edit Scores** to revise.")
            if st.button("✏️ Edit Scores", key=f"prelims_edit_{comp_id}"):
                st.session_state[editing_key] = True
                st.rerun()
        if editing:
            if st.button("✕ Cancel Edit", key=f"prelims_cancel_{comp_id}"):
                st.session_state[editing_key] = False
                st.rerun()

    # Scoring legend
    st.markdown(
        '<p style="font-size:0.77rem;color:rgba(0,75,135,0.65);margin:0 0 4px;">'
        '&nbsp;&nbsp;'
        '<span style="font-weight:700;color:#FF6666;">0</span> = Not scored&ensp;·&ensp;'
        '<span style="font-weight:700;color:rgba(160,180,220,0.85);">1–3</span> = Needs work&ensp;·&ensp;'
        '<span style="font-weight:700;color:rgba(160,180,220,0.85);">4–6</span> = Meets expectations&ensp;·&ensp;'
        '<span style="font-weight:700;color:#4CD4A0;">7–9</span> = Excellent&ensp;·&ensp;'
        '<span style="font-weight:700;color:#F0A030;">10</span> = Outstanding'
        '</p>',
        unsafe_allow_html=True,
    )

    disabled = view_only or (scored and not editing)

    # Use st.form when editable to batch all chip interactions into a single rerun
    # on Save; fall back to a no-op context when the form is read-only.
    form_ctx = (
        st.form(key=f"prelims_form_{judge_id}_{comp_id}")
        if not disabled
        else contextlib.nullcontext()
    )

    with form_ctx:
        answers = {}
        for i, q in enumerate(questions, 1):
            stored_raw    = int(existing.get(q["id"], 0))
            stored_choice = int(stored_raw / 10) if stored_raw else 0

            # Question card header
            st.markdown(
                f'<div class="q-header">'
                f'  <span class="q-num">Q{i}</span>'
                f'  <span class="q-text">{q["prompt"]}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # Score chips (0–10 horizontal radio, label hidden — shown in q-header above)
            choice = st.radio(
                q["prompt"],
                options=list(range(0, 11)),
                index=stored_choice,
                horizontal=True,
                format_func=lambda x: str(x),
                key=f"q_chip_{judge_id}_{comp_id}_{q['id']}",
                label_visibility="collapsed",
                disabled=disabled,
            )
            answers[q["id"]] = choice

            # Score result label (bottom cap of the card)
            st.markdown(
                f'<div class="score-result">→ &nbsp;{_score_label(choice)}</div>',
                unsafe_allow_html=True,
            )

        # ── Additional comments ────────────────────────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        comments = st.text_area(
            "Additional Comments / Notes (optional)",
            value=existing_comments,
            placeholder="Enter any feedback, observations, or notes for this team…",
            key=f"prelims_comments_{judge_id}_{comp_id}",
            disabled=disabled,
            height=100,
        )

        if not disabled:
            st.markdown("<br>", unsafe_allow_html=True)
            col_save, _ = st.columns([3, 5])
            with col_save:
                submitted = st.form_submit_button(
                    "Save Scores", type="primary", use_container_width=True
                )
            if submitted:
                missing = [q for q in questions if q["id"] not in answers]
                if missing:
                    st.error(
                        f"Please score all {len(missing)} remaining "
                        f"question{'s' if len(missing) != 1 else ''} before saving."
                    )
                else:
                    cleaned = {qid: val * 10 for qid, val in answers.items()}
                    save_answers_for_judge(judge_id, comp_id, cleaned, comments=comments)
                    st.session_state[editing_key] = False
                    st.session_state["score_saved"] = True
                    st.rerun()


# ── Main entry point ───────────────────────────────────────────────────────────

def show():
    user     = st.session_state.get("user")
    is_judge = user and user.get("role") == "judge"

    if not is_judge:
        st.error("Judge access required.")
        st.stop()

    # Finals judges must not land here
    if user.get("judge_round", "prelims") == "finals":
        st.error("⛔ This page is for Prelims judges only.")
        st.stop()

    # ── Load judge details (needed in navbar) ─────────────────────────────────
    username      = user.get("username", "Judge")
    judge_id      = user.get("judge_id")
    judge         = get_judge_by_id(judge_id) if judge_id else None
    judge_name    = judge.get("name", username) if judge else username
    assigned_room = judge.get("prelim_room") if judge else None

    # ── CSS ────────────────────────────────────────────────────────────────────
    _render_css()

    # ── Top navbar: logos (left)  ·  signed in + logout (right) ──────────────
    ah_tag = (
        _b64_tag(_LOGO_AH_WHITE, "height:42px;object-fit:contain;", "AutoHack 2026")
        or _b64_tag(_LOGO_AH_SVG, "height:42px;object-fit:contain;", "AutoHack 2026")
        or _b64_tag(_LOGO_AH_PNG, "height:42px;object-fit:contain;", "AutoHack 2026")
    )
    gc_tag = _b64_tag(
        _LOGO_GC_PNG, "height:28px;object-fit:contain;opacity:0.82;", "Georgian College"
    )

    nav_logo, nav_right = st.columns([5, 4])
    with nav_logo:
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:16px;padding:8px 0 6px;">'
            f'  {ah_tag}'
            f'  <span style="color:rgba(255,255,255,0.20);font-size:2rem;'
            f'font-weight:100;line-height:1;padding:0 2px;">|</span>'
            f'  {gc_tag}'
            f'</div>',
            unsafe_allow_html=True,
        )
    with nav_right:
        sub_user, sub_btn = st.columns([3, 1])
        with sub_user:
            st.markdown(
                f'<p class="ah-nav-user" style="text-align:right; font-size:14px;">'
                f'Signed in as&nbsp;<strong>{username}</strong></p>',
                unsafe_allow_html=True,
            )
        with sub_btn:
            if st.button("Log Out", key="prelims_signout", type="primary"):
                st.session_state["_do_logout"] = True
                st.rerun()

    # ── Subtitle + stripe (kept as-is) ────────────────────────────────────────
    st.markdown(
        '<div style="text-align:center;padding-top:8px;'
        'border-top:1px solid rgba(255,255,255,0.07);">'
        '  <p class="ah-subtitle">Prelims Scoring</p>'
        '  <div class="ah-stripe"></div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Greeting + room badge row (greeting left · room badge right) ───────────
    _room_badge = (
        f'<span class="room-tag">&#128205; Room &nbsp;<strong>{assigned_room}</strong></span>'
        if assigned_room else
        '<span class="room-tag" style="border-color:rgba(204,0,0,0.35);'
        'background:rgba(204,0,0,0.10);color:rgba(255,160,160,0.85);">'
        '&#9888; No room assigned</span>'
    )
    st.markdown(
        f'<div style="display:flex;align-items:center;justify-content:space-between;'
        f'margin-top:10px;padding:0 4px;">'
        f'<span style="color:#FFFFFF;font-size:0.95rem;font-weight:400;">'
        f'Hello&nbsp;<strong>{judge_name}</strong>, welcome to Judge Portal!</span>'
        f'{_room_badge}'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.divider()

    # Toast on successful save
    if st.session_state.pop("score_saved", False):
        st.toast("Scores saved!", icon="✅")

    # ── Intro message (always shown if set) ───────────────────────────────────
    intro = get_intro_message()
    if intro:
        st.info(intro)

    # ── Guard: judge profile ──────────────────────────────────────────────────
    if not judge:
        st.error("Judge profile missing — please contact admin.")
        st.stop()

    # ── Load scoring questions ────────────────────────────────────────────────
    questions = get_questions()
    if not questions:
        st.warning("No scoring questions have been added yet. Contact admin.")
        return

    # ── Load teams for this room ──────────────────────────────────────────────
    team_data     = get_teams_booked_in_room(assigned_room) if assigned_room else []
    team_info_map = {t["team_name"]: t for t in team_data}

    # Auto-create competitor entries
    competitors = []
    for t in team_data:
        comp = get_or_create_competitor_for_team(t["team_name"])
        competitors.append(comp)

    all_scores = get_scores_for_judge_all(judge_id) if judge_id else {}

    # ── Team selector ─────────────────────────────────────────────────────────
    st.markdown('<p class="ah-section">Select Team to Score</p>', unsafe_allow_html=True)

    # Build slot map so we can show each team's booked time in the dropdown
    slot_map = {t["team_name"]: t.get("slot_label", "") for t in team_data}

    option_labels = []
    comp_by_label = {}
    for c in competitors:
        is_scored = c["id"] in all_scores and all_scores[c["id"]] > 0
        slot      = slot_map.get(c["name"], "")
        slot_str  = f"  —  {slot}" if slot else ""
        label     = f"{'✅' if is_scored else '⏳'}  {c['name']}{slot_str}"
        option_labels.append(label)
        comp_by_label[label] = c

    if option_labels:
        selected_label = st.selectbox(
            "Select a team to score", option_labels, label_visibility="collapsed"
        )
    else:
        st.selectbox(
            "Select a team to score", ["— No teams yet —"], label_visibility="collapsed"
        )
        if not assigned_room:
            st.info(
                "⚠️ You haven't been assigned to a room yet. "
                "Please contact the event organisers — details above."
            )
        else:
            st.info(
                f"No teams have booked a prelims slot in **Room {assigned_room}** yet. "
                "Check back once bookings are made."
            )
        return

    # # ── Metrics ───────────────────────────────────────────────────────────────
    # scored_count = sum(
    #     1 for c in competitors
    #     if c["id"] in all_scores and all_scores[c["id"]] > 0
    # )
    # c1, c2, c3 = st.columns(3)
    # c1.metric("Teams in Room", len(competitors))
    # c2.metric("Scored",        scored_count)
    # c3.metric("Remaining",     len(competitors) - scored_count)

    # st.divider()

    # ── Team info card ────────────────────────────────────────────────────────
    comp = comp_by_label[selected_label]
    if comp["name"] in team_info_map:
        _render_team_card(team_info_map[comp["name"]])

    # ── Scoring form ──────────────────────────────────────────────────────────
    st.markdown('<p class="ah-section">Score This Team</p>', unsafe_allow_html=True)
    _render_scoring_form(judge_id, comp["id"], comp["name"], questions, view_only=False)

    st.divider()
    st.markdown(
        '<p style="font-size: 14px;">'
        'Having trouble? Contact us at '
        '<a href="mailto:Shubhneet.Sandhu@GeorgianCollege.ca" style="color: rgb(107, 159, 228);">Shubhneet.Sandhu@GeorgianCollege.ca</a> '
        'or '
        '<a href="mailto:Brunilda.Xhaferllari@GeorgianCollege.ca" style="color: rgb(107, 159, 228);">Brunilda.Xhaferllari@GeorgianCollege.ca</a>.'
        '</p>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<p style="text-align:center;color:rgba(180,190,215,0.30);'
        'font-size:0.72rem;margin-top:8px;">Powered by Research and Innovation, Georgian College</p>',
        unsafe_allow_html=True,
    )

    #     # ── Contact info (always shown) ───────────────────────────────────────────
    # st.divider()
    # st.caption(
    #     f"Questions or issues? Contact "
    #     f"**Shubhneet Sandhu** — [{_CONTACT_SHUBHNEET}](mailto:{_CONTACT_SHUBHNEET})"
    #     f"&nbsp;·&nbsp;"
    #     f"**Brunilda** — [{_CONTACT_BRUNILDA}](mailto:{_CONTACT_BRUNILDA})"
    # )
