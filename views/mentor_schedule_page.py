"""
views/mentor_schedule_page.py

Read-only mentor schedule calendar — password-protected.
Accessible via ?page=mentor_schedule.

Login credentials (hardcoded, no DB lookup needed for mentors):
  Username : AutoHackMentor
  Password : AH2026!Mentor

Displays all team mentor session bookings in a calendar-style grid,
split by day (Friday Mar 6 / Saturday Mar 7), with rooms as columns
and time slots as rows.
"""

import os
import base64
import hashlib
import streamlit as st

from db import (
    MENTOR_ROOM_MAP,
    SCHED_FRIDAY_SLOTS,
    SCHED_SATURDAY_SLOTS,
    get_all_mentor_bookings,
)

# ── Mentor portal credentials ──────────────────────────────────────────────────
_MENTOR_USERNAME = "AutoHackMentor"
# Store password as SHA-256 so the plain string isn't sitting in code at runtime
_MENTOR_PASSWORD_HASH = hashlib.sha256("AH2026!Mentor".encode()).hexdigest()

_SESSION_KEY = "mentor_authenticated"  # st.session_state flag

# ── Asset paths ────────────────────────────────────────────────────────────────
_LOGO_AH_SVG   = os.path.join("assets", "autohack_logo.svg")
_LOGO_AH_PNG   = os.path.join("assets", "autohack_logo.png")
_LOGO_AH_WHITE = os.path.join("assets", "autohack_logo_white.png")
_LOGO_GC_PNG   = os.path.join("assets", "georgian_logo.png")

_BG_URL = (
    "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7"
    "?auto=format&fit=crop&w=1920&q=80"
)

# ── CSS ────────────────────────────────────────────────────────────────────────
_CSS = f"""
<style>
.stApp {{
    background-image:
        linear-gradient(rgba(0,0,0,0.82), rgba(0,0,0,0.88)),
        url('{_BG_URL}');
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
    min-height: 100vh;
}}
.main .block-container {{
    background: rgba(10, 12, 22, 0.68) !important;
    backdrop-filter: blur(18px) !important;
    -webkit-backdrop-filter: blur(18px) !important;
    border-radius: 20px !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    padding: 2.5rem 3rem !important;
    max-width: 1060px !important;
    margin-top: 1.5rem !important;
    margin-bottom: 2rem !important;
    box-shadow: 0 8px 60px rgba(0,0,0,0.60) !important;
}}
.ah-subtitle {{
    color: rgba(200,210,230,0.70); font-size: 0.95rem;
    letter-spacing: 2.5px; text-transform: uppercase; font-weight: 300; margin: 0;
}}
.ah-stripe {{
    height: 3px;
    background: linear-gradient(90deg, #CC0000 50%, #4A80D4 50%);
    border-radius: 2px; width: 55%; margin: 16px auto 0;
}}
.ah-section {{
    color: #FF4040; font-weight: 700; font-size: 0.80rem;
    text-transform: uppercase; letter-spacing: 1.4px;
    border-left: 3px solid #CC0000; padding: 2px 0 2px 10px; margin: 6px 0 12px;
}}

/* Login form card */
.login-card {{
    background: rgba(16, 20, 42, 0.72);
    border: 1px solid rgba(74,128,212,0.30);
    border-radius: 16px;
    padding: 32px 36px 28px;
    max-width: 420px;
    margin: 0 auto;
    box-shadow: 0 8px 40px rgba(0,0,0,0.40);
}}
.login-title {{
    color: #FFFFFF;
    font-size: 1.10rem;
    font-weight: 700;
    text-align: center;
    margin: 0 0 6px;
    letter-spacing: 0.5px;
}}
.login-sub {{
    color: rgba(180,200,235,0.55);
    font-size: 0.82rem;
    text-align: center;
    margin: 0 0 24px;
    letter-spacing: 0.3px;
}}

/* Input fields */
[data-baseweb="base-input"] {{
    background: rgba(18,20,40,0.92) !important;
    border: 1px solid rgba(255,255,255,0.16) !important;
    border-radius: 8px !important;
}}
[data-baseweb="base-input"] input {{
    background: transparent !important;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
}}
label {{ color: rgba(200,215,245,0.80) !important; font-size: 0.86rem !important; }}

/* Primary button */
[data-testid="stBaseButton-primary"] {{
    background-color: #CC0000 !important; border-color: #CC0000 !important;
    color: white !important; font-weight: 700 !important;
    font-size: 0.95rem !important; letter-spacing: 0.8px !important;
    border-radius: 8px !important; text-transform: uppercase !important;
    box-shadow: 0 4px 24px rgba(204,0,0,0.45) !important;
}}
[data-testid="stBaseButton-primary"]:hover {{
    background-color: #EE1111 !important;
    box-shadow: 0 6px 32px rgba(204,0,0,0.65) !important;
    transform: translateY(-1px) !important;
}}

/* Signed-in sub-bar */
.mentor-subbar {{
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 12px;
    padding: 8px 0 4px;
}}
.mentor-badge {{
    display: inline-block;
    background: rgba(74,128,212,0.14);
    border: 1px solid rgba(74,128,212,0.35);
    color: rgba(200,215,245,0.80);
    font-size: 0.80rem;
    font-weight: 600;
    padding: 5px 14px;
    border-radius: 20px;
    letter-spacing: 0.4px;
}}

/* Day banner */
.cal-day-banner {{
    background: linear-gradient(90deg, rgba(204,0,0,0.14) 0%, rgba(74,128,212,0.12) 100%);
    border-left: 4px solid #CC0000;
    border-radius: 0 10px 10px 0;
    padding: 12px 20px;
    margin: 4px 0 14px;
}}
.cal-day-title {{ color: #FFFFFF; font-size: 1.05rem; font-weight: 700; margin: 0; }}
.cal-day-sub   {{ color: rgba(190,205,230,0.65); font-size: 0.80rem; margin: 3px 0 0; }}

/* Grid header */
.cal-grid-header {{
    color: #6B9FE4; font-weight: 700; font-size: 0.80rem;
    text-transform: uppercase; text-align: center;
    padding-bottom: 6px;
    border-bottom: 1px solid rgba(74,128,212,0.35);
    line-height: 1.35;
}}
.cal-grid-header-left {{
    color: #6B9FE4; font-weight: 700; font-size: 0.80rem;
    text-transform: uppercase;
    padding-bottom: 6px;
    border-bottom: 1px solid rgba(74,128,212,0.35);
}}
.cal-time {{
    color: rgba(215,225,245,0.85);
    font-size: 0.86rem;
    padding-top: 8px;
    line-height: 1.4;
}}

/* Calendar cells */
.cal-open {{
    background: rgba(30,80,30,0.12);
    border: 1px dashed rgba(60,200,80,0.22);
    border-radius: 8px;
    padding: 7px 8px;
    text-align: center;
    color: rgba(100,220,120,0.45);
    font-size: 0.78rem;
    font-style: italic;
    margin: 2px 0;
    min-height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
}}
.cal-team {{
    background: rgba(26,75,153,0.28);
    border: 1px solid rgba(74,128,212,0.42);
    border-radius: 7px;
    padding: 6px 8px;
    color: rgba(215,228,255,0.93);
    font-size: 0.80rem;
    font-weight: 600;
    margin: 2px 0;
    text-align: center;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}}
.cal-team-full {{
    background: rgba(140,30,30,0.22);
    border: 1px solid rgba(204,0,0,0.38);
    border-radius: 7px;
    padding: 6px 8px;
    color: rgba(255,200,200,0.90);
    font-size: 0.80rem;
    font-weight: 600;
    margin: 2px 0;
    text-align: center;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}}

/* Metric cards */
[data-testid="stMetric"] {{
    background: rgba(15,18,40,0.50) !important;
    border: 1px solid rgba(74,128,212,0.25) !important;
    border-radius: 12px !important;
    padding: 12px 16px !important;
}}
[data-testid="stMetricLabel"]  {{ color: rgba(180,200,235,0.75) !important; font-size: 0.78rem !important; }}
[data-testid="stMetricValue"]  {{ color: #FFFFFF !important; font-size: 1.6rem !important; font-weight: 700 !important; }}

/* General text */
.stMarkdown p, .stMarkdown li {{ color: rgba(225,230,245,0.90) !important; }}
hr {{ border-color: rgba(255,255,255,0.10) !important; }}
</style>
"""


# ── Asset helpers ──────────────────────────────────────────────────────────────

def _b64_tag(path: str, style: str, alt: str = "") -> str:
    if not os.path.exists(path):
        return ""
    ext  = os.path.splitext(path)[1].lstrip(".").lower()
    mime = "image/svg+xml" if ext == "svg" else f"image/{ext}"
    with open(path, "rb") as fh:
        b64 = base64.b64encode(fh.read()).decode()
    return f'<img src="data:{mime};base64,{b64}" style="{style}" alt="{alt}">'


def _render_header():
    st.markdown(_CSS, unsafe_allow_html=True)

    ah_tag = (
        _b64_tag(_LOGO_AH_WHITE,
                 "width:100%;max-width:560px;height:auto;object-fit:contain;",
                 "AutoHack 2026")
        or _b64_tag(_LOGO_AH_SVG,
                    "width:100%;max-width:560px;height:auto;object-fit:contain;",
                    "AutoHack 2026")
        or _b64_tag(_LOGO_AH_PNG,
                    "width:100%;max-width:560px;height:auto;object-fit:contain;",
                    "AutoHack 2026")
    )
    gc_tag = _b64_tag(
        _LOGO_GC_PNG,
        "height:44px;object-fit:contain;opacity:0.80;",
        "Georgian College"
    )

    banner = (
        '<div style="'
        '  position:relative;'
        '  background:rgba(8,10,20,0.70);'
        '  border-radius:16px;'
        '  padding:28px 24px 20px;'
        '  margin-bottom:4px;'
        '  text-align:center;'
        '  border:1px solid rgba(255,255,255,0.07);'
        '">'
        f'  {ah_tag}'
        + (
            '<div style="position:absolute;bottom:14px;right:18px;">'
            f'{gc_tag}'
            '</div>'
            if gc_tag else ""
        )
        + '</div>'
    )
    subtitle = (
        '<div style="text-align:center;padding-top:12px;">'
        '  <p class="ah-subtitle">Mentor Schedule</p>'
        '  <div class="ah-stripe"></div>'
        '</div>'
    )
    st.markdown(banner + subtitle, unsafe_allow_html=True)


# ── Auth helpers ───────────────────────────────────────────────────────────────

def _check_password(username: str, password: str) -> bool:
    if username.strip() != _MENTOR_USERNAME:
        return False
    return hashlib.sha256(password.encode()).hexdigest() == _MENTOR_PASSWORD_HASH


def _render_login():
    """Render the branded login form. Stops execution after rendering."""
    _render_header()

    st.markdown("<br>", unsafe_allow_html=True)

    # Centred login card
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown(
            '<div class="login-card">'
            '  <p class="login-title">🔐 Mentor Portal</p>'
            '  <p class="login-sub">Sign in to view the session schedule</p>'
            '</div>',
            unsafe_allow_html=True,
        )

        username = st.text_input("Username", key="mentor_login_user")
        password = st.text_input("Password", type="password", key="mentor_login_pw")

        if st.button("Sign In", type="primary", use_container_width=True,
                     key="mentor_login_btn"):
            if _check_password(username, password):
                st.session_state[_SESSION_KEY] = True
                st.rerun()
            else:
                st.error("Incorrect username or password.")

        st.markdown(
            '<p style="color:rgba(180,195,225,0.40);font-size:0.76rem;'
            'text-align:center;margin-top:18px;">'
            'Need access? Contact '
            '<a href="mailto:Shubhneet.Sandhu@GeorgianCollege.ca" '
            'style="color:rgba(107,159,228,0.70);">'
            'Shubhneet.Sandhu@GeorgianCollege.ca</a></p>',
            unsafe_allow_html=True,
        )

    st.stop()


# ── Data helpers ───────────────────────────────────────────────────────────────

def _short(slot_label: str) -> str:
    """Strip day prefix: 'Fri Mar 6 · 6:20 – 6:40 PM' → '6:20 – 6:40 PM'."""
    return slot_label.split("\u00b7", 1)[-1].strip()


def _rooms_ordered() -> list:
    return list(dict.fromkeys(MENTOR_ROOM_MAP.values()))


def _mentors_per_room() -> dict:
    rooms = _rooms_ordered()
    return {r: [m for m, rm in MENTOR_ROOM_MAP.items() if rm == r] for r in rooms}


def _build_schedule_map(bookings: list) -> dict:
    """Build {(slot_label, room): [team_name, ...]} from all mentor bookings."""
    result: dict = {}
    for b in bookings:
        slot = b["slot_label"]
        room = MENTOR_ROOM_MAP.get(b.get("mentor_name", ""), None)
        if room is None:
            continue
        result.setdefault((slot, room), []).append(b["team_name"])
    return result


# ── Calendar grid renderer ─────────────────────────────────────────────────────

def _render_day_grid(slots: list, schedule_map: dict, rooms: list, mpr: dict):
    col_widths = [1.8] + [1.0] * len(rooms)

    # Header row
    hcols = st.columns(col_widths)
    hcols[0].markdown('<p class="cal-grid-header-left">Time</p>', unsafe_allow_html=True)
    for i, room in enumerate(rooms, start=1):
        cap = len(mpr[room])
        hcols[i].markdown(
            f'<p class="cal-grid-header">Room {room}'
            f'<br><span style="font-weight:400;opacity:0.55;font-size:0.72rem;">'
            f'{cap} mentor{"s" if cap > 1 else ""}</span></p>',
            unsafe_allow_html=True,
        )

    # Slot rows
    for slot in slots:
        row = st.columns(col_widths)
        row[0].markdown(
            f'<p class="cal-time">{_short(slot)}</p>',
            unsafe_allow_html=True,
        )
        for i, room in enumerate(rooms, start=1):
            teams   = schedule_map.get((slot, room), [])
            cap     = len(mpr[room])
            is_full = len(teams) >= cap

            if not teams:
                row[i].markdown('<div class="cal-open">Open</div>', unsafe_allow_html=True)
            else:
                cell_class = "cal-team-full" if is_full else "cal-team"
                inner = "".join(f'<div class="{cell_class}">{t}</div>' for t in teams)
                row[i].markdown(inner, unsafe_allow_html=True)


# ── Main entry point ───────────────────────────────────────────────────────────

def show():
    # ── Auth gate ──────────────────────────────────────────────────────────────
    if not st.session_state.get(_SESSION_KEY):
        _render_login()
        return  # _render_login() calls st.stop() but return is here for clarity

    # ── Authenticated: render page ─────────────────────────────────────────────
    _render_header()

    # Sign-out sub-bar (right-aligned, below banner)
    st.markdown("<br>", unsafe_allow_html=True)
    col_badge, col_btn = st.columns([6, 2])
    with col_badge:
        st.markdown(
            '<div style="display:flex;align-items:center;gap:10px;">'
            '<span class="mentor-badge">👤 Mentor Portal</span>'
            '<span style="color:rgba(180,195,225,0.45);font-size:0.80rem;">'
            f'Signed in as <strong style="color:rgba(200,215,245,0.75);">'
            f'{_MENTOR_USERNAME}</strong></span>'
            '</div>',
            unsafe_allow_html=True,
        )
    with col_btn:
        if st.button("↩ Sign Out", type="primary", use_container_width=True,
                     key="mentor_signout"):
            st.session_state.pop(_SESSION_KEY, None)
            st.rerun()

    st.divider()

    st.markdown(
        "This page shows all **mentor session bookings** made by student teams. "
        "Use it to see which teams are visiting your room and when. "
        "The schedule refreshes automatically whenever this page is loaded."
    )
    st.divider()

    # ── Load data ──────────────────────────────────────────────────────────────
    bookings     = get_all_mentor_bookings()
    schedule_map = _build_schedule_map(bookings)
    rooms        = _rooms_ordered()
    mpr          = _mentors_per_room()

    total_possible = sum(len(mpr[r]) for r in rooms) * (
        len(SCHED_FRIDAY_SLOTS) + len(SCHED_SATURDAY_SLOTS)
    )
    fri_booked   = sum(1 for b in bookings if b["slot_label"].startswith("Fri"))
    sat_booked   = sum(1 for b in bookings if b["slot_label"].startswith("Sat"))
    total_booked = len(bookings)

    # ── Metrics ────────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Booked",       total_booked)
    c2.metric("Friday Sessions",    fri_booked)
    c3.metric("Saturday Sessions",  sat_booked)
    c4.metric("Remaining Capacity", total_possible - total_booked)

    # ── Legend ─────────────────────────────────────────────────────────────────
    st.markdown(
        '<p style="color:rgba(180,195,225,0.55);font-size:0.80rem;margin:4px 0 0;">'
        '&nbsp;&nbsp;'
        '<span style="color:rgba(100,220,120,0.50);font-style:italic;">Open</span>'
        ' — no bookings &nbsp;·&nbsp; '
        '<span style="color:rgba(215,228,255,0.93);">Blue cell</span>'
        ' — team booked (capacity remaining) &nbsp;·&nbsp; '
        '<span style="color:rgba(255,200,200,0.90);">Red cell</span>'
        ' — room fully booked at this time'
        '</p>',
        unsafe_allow_html=True,
    )

    st.divider()

    # ── Friday grid ────────────────────────────────────────────────────────────
    st.markdown(
        '<div class="cal-day-banner">'
        '  <p class="cal-day-title">📅 Friday, March 6</p>'
        '  <p class="cal-day-sub">6:20 PM – 8:00 PM &nbsp;·&nbsp; 5 slots × 20 min</p>'
        '</div>',
        unsafe_allow_html=True,
    )
    _render_day_grid(SCHED_FRIDAY_SLOTS, schedule_map, rooms, mpr)

    st.divider()

    # ── Saturday grid ──────────────────────────────────────────────────────────
    st.markdown(
        '<div class="cal-day-banner">'
        '  <p class="cal-day-title">📅 Saturday, March 7</p>'
        '  <p class="cal-day-sub">10:00 AM – 1:20 PM &nbsp;·&nbsp; 10 slots × 20 min</p>'
        '</div>',
        unsafe_allow_html=True,
    )
    _render_day_grid(SCHED_SATURDAY_SLOTS, schedule_map, rooms, mpr)

    st.divider()
    st.caption(
        "Questions? Contact "
        "[Shubhneet.Sandhu@GeorgianCollege.ca](mailto:Shubhneet.Sandhu@GeorgianCollege.ca) "
        "or "
        "[Brunilda.Xhaferllari@GeorgianCollege.ca](mailto:Brunilda.Xhaferllari@GeorgianCollege.ca)."
    )
