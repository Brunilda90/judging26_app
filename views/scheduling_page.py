"""
views/scheduling_page.py

Public-facing mentor & robot scheduling portal.
Accessible via ?page=schedule (no login required).

Teams can book up to 2 mentor sessions and up to 2 robot demo sessions
across two time windows:
  - Friday  Mar 6, 2026  6:20 PM – 8:00 PM  (5 × 20-min slots)
  - Saturday Mar 7, 2026 10:00 AM – 1:20 PM (10 × 20-min slots)
"""

import os
import base64
import streamlit as st

from db import (
    MENTOR_NAMES,
    SCHED_ROBOT_ROOMS,
    SCHED_FRIDAY_SLOTS,
    SCHED_SATURDAY_SLOTS,
    SCHED_ALL_SLOTS,
    MAX_MENTOR_BOOKINGS,
    MAX_ROBOT_BOOKINGS,
    get_bookable_team_names,
    get_team_registrations,
    get_mentor_bookings_for_team,
    get_robot_bookings_for_team,
    get_mentor_booked_map,
    get_robot_booked_map,
    create_mentor_booking,
    create_robot_booking,
    cancel_mentor_booking,
    cancel_robot_booking,
)

# ── Asset paths ─────────────────────────────────────────────────────────────────
_LOGO_AH_SVG   = os.path.join("assets", "autohack_logo.svg")
_LOGO_AH_PNG   = os.path.join("assets", "autohack_logo.png")
_LOGO_AH_WHITE = os.path.join("assets", "autohack_logo_white.png")
_LOGO_GC_PNG   = os.path.join("assets", "georgian_logo.png")

_BG_URL = (
    "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7"
    "?auto=format&fit=crop&w=1920&q=80"
)

# ── CSS ─────────────────────────────────────────────────────────────────────────
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
    max-width: 1020px !important;
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
.ah-info-card {{
    background: rgba(26,75,153,0.15);
    border: 1px solid rgba(74,128,212,0.35);
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 12px;
}}
.ah-info-card p {{ color: rgba(220,230,250,0.90) !important; margin: 4px 0 !important; }}
.ah-info-label {{ color: #6B9FE4 !important; font-weight: 600 !important; font-size: 0.82rem !important; text-transform: uppercase; letter-spacing: 0.8px; }}

/* Booking confirmation cards */
.ah-booking-card {{
    background: linear-gradient(135deg, rgba(20,60,140,0.30) 0%, rgba(10,12,22,0.85) 100%);
    border: 1px solid rgba(74,128,212,0.55);
    border-radius: 12px;
    padding: 14px 18px;
    margin-bottom: 10px;
}}
.ah-booking-card p {{ color: rgba(220,230,250,0.90) !important; margin: 3px 0 !important; font-size: 0.92rem; }}
.ah-booking-card strong {{ color: #FFFFFF !important; }}

/* Availability grid cells */
.slot-taken {{
    background: rgba(180,30,30,0.28);
    border: 1px solid rgba(204,0,0,0.50);
    border-radius: 6px; padding: 4px 6px; text-align: center;
    color: rgba(255,160,160,0.85); font-size: 0.75rem; font-weight: 600;
    margin: 1px 0;
}}
.slot-mine {{
    background: rgba(26,75,153,0.55);
    border: 2px solid #4A80D4;
    border-radius: 6px; padding: 4px 6px; text-align: center;
    color: #FFFFFF; font-size: 0.75rem; font-weight: 700;
    margin: 1px 0;
}}
.slot-free {{
    background: rgba(40,100,40,0.25);
    border: 1px solid rgba(60,200,80,0.40);
    border-radius: 6px; padding: 4px 6px; text-align: center;
    color: rgba(120,240,140,0.90); font-size: 0.75rem; font-weight: 600;
    margin: 1px 0;
}}
.slot-label-cell {{
    color: rgba(220,230,250,0.80); font-size: 0.80rem; padding-top: 5px;
}}
.grid-header {{
    color: #6B9FE4; font-weight: 700; font-size: 0.75rem; text-transform: uppercase;
    text-align: center; padding-bottom: 4px;
    border-bottom: 1px solid rgba(74,128,212,0.35);
}}
.day-divider {{
    color: rgba(220,160,0,0.80); font-size: 0.78rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 1px;
    margin: 8px 0 4px;
}}

/* General text */
.stMarkdown p, .stMarkdown li {{ color: rgba(225,230,245,0.90) !important; }}
label, .stRadio label {{ color: rgba(220,228,245,0.90) !important; }}
[data-baseweb="base-input"] {{ background: rgba(18,20,40,0.92) !important; border: 1px solid rgba(255,255,255,0.16) !important; border-radius: 8px !important; }}
[data-baseweb="base-input"] input {{ background: transparent !important; color: #FFFFFF !important; -webkit-text-fill-color: #FFFFFF !important; }}
[data-testid="stBaseButton-primary"] {{
    background-color: #CC0000 !important; border-color: #CC0000 !important;
    color: white !important; font-weight: 700 !important; border-radius: 8px !important;
    text-transform: uppercase !important; box-shadow: 0 4px 24px rgba(204,0,0,0.45) !important;
}}
[data-testid="stBaseButton-primary"]:hover {{
    background-color: #EE1111 !important; box-shadow: 0 6px 32px rgba(204,0,0,0.65) !important;
    transform: translateY(-1px) !important;
}}
hr {{ border-color: rgba(255,255,255,0.10) !important; }}
</style>
"""


# ── Asset helpers ────────────────────────────────────────────────────────────────

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
        ) +
        '</div>'
    )

    subtitle = (
        '<div style="text-align:center;padding-top:12px;">'
        '  <p class="ah-subtitle">Mentor &amp; Robot Scheduling</p>'
        '  <div class="ah-stripe"></div>'
        '</div>'
    )

    st.markdown(banner + subtitle, unsafe_allow_html=True)


# ── Registration lookup ──────────────────────────────────────────────────────────

def _get_reg_for_team(team_name: str):
    for status in ("pending", "approved"):
        for r in get_team_registrations(status=status):
            if r["team_name"] == team_name:
                return r
    return None


# ── Slot key helpers ─────────────────────────────────────────────────────────────

def _mentor_key(slot_label: str, mentor_name: str) -> str:
    return f"{slot_label}||{mentor_name}"


def _robot_key(slot_label: str, room: str) -> str:
    return f"{slot_label}||{room}"


def _is_friday_slot(slot_label: str) -> bool:
    return slot_label.startswith("Fri")


# ── Availability grid ────────────────────────────────────────────────────────────

def _render_mentor_grid(booked_map: dict, my_team: str):
    """Read-only availability grid: rows = slots, columns = mentors."""
    n = len(MENTOR_NAMES)
    col_widths = [2.0] + [0.85] * n

    # Header
    hcols = st.columns(col_widths)
    hcols[0].markdown('<p class="grid-header">Time Slot</p>', unsafe_allow_html=True)
    for i, m in enumerate(MENTOR_NAMES, start=1):
        short = m.replace("Mentor ", "M")
        hcols[i].markdown(f'<p class="grid-header">{short}</p>', unsafe_allow_html=True)

    last_day = None
    for slot in SCHED_ALL_SLOTS:
        day = "Friday" if _is_friday_slot(slot) else "Saturday"
        if day != last_day:
            last_day = day
            day_cols = st.columns(col_widths)
            day_cols[0].markdown(
                f'<p class="day-divider">&#9654; {day}</p>',
                unsafe_allow_html=True,
            )
        row = st.columns(col_widths)
        # Strip day prefix for a compact display
        short_slot = slot.split("\u00b7", 1)[-1].strip()
        row[0].markdown(
            f'<p class="slot-label-cell">{short_slot}</p>',
            unsafe_allow_html=True,
        )
        for i, mentor in enumerate(MENTOR_NAMES, start=1):
            occupant = booked_map.get(_mentor_key(slot, mentor))
            if occupant and occupant == my_team:
                row[i].markdown('<div class="slot-mine">&#11088; You</div>', unsafe_allow_html=True)
            elif occupant:
                row[i].markdown('<div class="slot-taken">Taken</div>', unsafe_allow_html=True)
            else:
                row[i].markdown('<div class="slot-free">Free</div>', unsafe_allow_html=True)


def _render_robot_grid(booked_map: dict, my_team: str):
    """Read-only availability grid: rows = slots, columns = robots (rooms)."""
    n = len(SCHED_ROBOT_ROOMS)
    col_widths = [2.0] + [1.0] * n

    hcols = st.columns(col_widths)
    hcols[0].markdown('<p class="grid-header">Time Slot</p>', unsafe_allow_html=True)
    for i, room in enumerate(SCHED_ROBOT_ROOMS, start=1):
        hcols[i].markdown(
            f'<p class="grid-header">Robot<br>{room}</p>', unsafe_allow_html=True
        )

    last_day = None
    for slot in SCHED_ALL_SLOTS:
        day = "Friday" if _is_friday_slot(slot) else "Saturday"
        if day != last_day:
            last_day = day
            day_cols = st.columns(col_widths)
            day_cols[0].markdown(
                f'<p class="day-divider">&#9654; {day}</p>',
                unsafe_allow_html=True,
            )
        row = st.columns(col_widths)
        short_slot = slot.split("\u00b7", 1)[-1].strip()
        row[0].markdown(
            f'<p class="slot-label-cell">{short_slot}</p>',
            unsafe_allow_html=True,
        )
        for i, room in enumerate(SCHED_ROBOT_ROOMS, start=1):
            occupant = booked_map.get(_robot_key(slot, room))
            if occupant and occupant == my_team:
                row[i].markdown('<div class="slot-mine">&#11088; You</div>', unsafe_allow_html=True)
            elif occupant:
                row[i].markdown('<div class="slot-taken">Taken</div>', unsafe_allow_html=True)
            else:
                row[i].markdown('<div class="slot-free">Free</div>', unsafe_allow_html=True)


# ── Mentor tab ───────────────────────────────────────────────────────────────────

def _mentor_tab(team_name: str):
    mentor_bookings = get_mentor_bookings_for_team(team_name)
    mentor_booked_map = get_mentor_booked_map()

    # ── Current bookings ──────────────────────────────────────────────────────
    st.markdown('<p class="ah-section">Your Mentor Bookings</p>', unsafe_allow_html=True)

    if mentor_bookings:
        for b in mentor_bookings:
            day_tag = "🟡 Friday" if _is_friday_slot(b["slot_label"]) else "🔵 Saturday"
            st.markdown(
                f'<div class="ah-booking-card">'
                f'<p><strong>{b["mentor_name"]}</strong> &nbsp;·&nbsp; {b["slot_label"]}'
                f' &nbsp;<span style="opacity:0.60;font-size:0.78rem;">({day_tag})</span></p>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button(
                f"Cancel – {b['mentor_name']} @ {b['slot_label'].split(chr(183),1)[-1].strip()}",
                key=f"cancel_mentor_{b['id']}",
            ):
                cancel_mentor_booking(b["id"])
                st.success("Mentor session cancelled.")
                st.rerun()
    else:
        st.info("No mentor sessions booked yet.")

    # ── Friday encouragement banner ───────────────────────────────────────────
    has_friday = any(_is_friday_slot(b["slot_label"]) for b in mentor_bookings)
    slots_used = len(mentor_bookings)

    if not has_friday and slots_used < MAX_MENTOR_BOOKINGS:
        st.warning(
            "⚠️ **Please prioritise a Friday evening mentor session (6:20–8:00 PM)!** "
            "Friday mentors can give you feedback while you still have Saturday to apply it. "
            "Book a Friday slot below — it makes a big difference."
        )

    if slots_used >= MAX_MENTOR_BOOKINGS:
        st.success(
            f"✅ You've booked all {MAX_MENTOR_BOOKINGS} mentor sessions. "
            "Cancel one above to change it."
        )
        st.divider()
        st.markdown('<p class="ah-section">Availability Overview</p>', unsafe_allow_html=True)
        _render_mentor_grid(mentor_booked_map, team_name)
        return

    # ── Booking form ──────────────────────────────────────────────────────────
    remaining = MAX_MENTOR_BOOKINGS - slots_used
    st.divider()
    st.markdown(
        f'<p class="ah-section">Book a Mentor Session '
        f'({remaining} slot{"s" if remaining > 1 else ""} remaining)</p>',
        unsafe_allow_html=True,
    )

    # Already-booked slots for this team (to avoid double-booking same time)
    team_mentor_slots = {b["slot_label"] for b in mentor_bookings}

    selected_mentor = st.selectbox(
        "Choose a mentor",
        options=MENTOR_NAMES,
        key="sched_mentor_pick",
    )

    # Build available slots for this mentor
    def _avail_slots_for_mentor(mentor):
        result = []
        for slot in SCHED_ALL_SLOTS:
            key = _mentor_key(slot, mentor)
            if key not in mentor_booked_map and slot not in team_mentor_slots:
                result.append(slot)
        return result

    avail = _avail_slots_for_mentor(selected_mentor)

    if not avail:
        st.warning(f"{selected_mentor} has no available slots (or you've already used those times).")
    else:
        # Split into Friday and Saturday option groups with a visual separator
        fri_options = [s for s in avail if _is_friday_slot(s)]
        sat_options = [s for s in avail if not _is_friday_slot(s)]

        display_options = []
        if fri_options:
            display_options += ["── Friday Mar 6 ──"] + fri_options
        if sat_options:
            display_options += ["── Saturday Mar 7 ──"] + sat_options

        raw_choice = st.selectbox(
            "Choose a time slot",
            options=display_options,
            key="sched_mentor_slot",
        )

        # Separator rows are not bookable
        is_separator = raw_choice.startswith("──")

        if not is_separator:
            if st.button("Book Mentor Session", type="primary", use_container_width=True):
                try:
                    create_mentor_booking(team_name, selected_mentor, raw_choice)
                    st.success(
                        f"🎉 Booked: **{selected_mentor}** at **{raw_choice}**"
                    )
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
        else:
            st.caption("Select a specific time slot (not a header).")

    # ── Availability overview ─────────────────────────────────────────────────
    st.divider()
    st.markdown('<p class="ah-section">Full Availability Overview</p>', unsafe_allow_html=True)
    _render_mentor_grid(mentor_booked_map, team_name)


# ── Robot tab ────────────────────────────────────────────────────────────────────

def _robot_tab(team_name: str):
    robot_bookings = get_robot_bookings_for_team(team_name)
    robot_booked_map = get_robot_booked_map()

    # Soft encourage
    st.info(
        "🤖 **Robot Demo Sessions** — Each team can book up to "
        f"{MAX_ROBOT_BOOKINGS} sessions. Give the robots a try!"
    )

    # ── Current bookings ──────────────────────────────────────────────────────
    st.markdown('<p class="ah-section">Your Robot Bookings</p>', unsafe_allow_html=True)

    if robot_bookings:
        for b in robot_bookings:
            day_tag = "🟡 Friday" if _is_friday_slot(b["slot_label"]) else "🔵 Saturday"
            st.markdown(
                f'<div class="ah-booking-card">'
                f'<p><strong>Robot in {b["room"]}</strong> &nbsp;·&nbsp; {b["slot_label"]}'
                f' &nbsp;<span style="opacity:0.60;font-size:0.78rem;">({day_tag})</span></p>'
                f'</div>',
                unsafe_allow_html=True,
            )
            short_slot = b["slot_label"].split("\u00b7", 1)[-1].strip()
            if st.button(
                f"Cancel – Robot {b['room']} @ {short_slot}",
                key=f"cancel_robot_{b['id']}",
            ):
                cancel_robot_booking(b["id"])
                st.success("Robot session cancelled.")
                st.rerun()
    else:
        st.info("No robot sessions booked yet.")

    slots_used = len(robot_bookings)

    if slots_used >= MAX_ROBOT_BOOKINGS:
        st.success(
            f"✅ You've booked all {MAX_ROBOT_BOOKINGS} robot sessions. "
            "Cancel one above to change it."
        )
        st.divider()
        st.markdown('<p class="ah-section">Availability Overview</p>', unsafe_allow_html=True)
        _render_robot_grid(robot_booked_map, team_name)
        return

    # ── Booking form ──────────────────────────────────────────────────────────
    remaining = MAX_ROBOT_BOOKINGS - slots_used
    st.divider()
    st.markdown(
        f'<p class="ah-section">Book a Robot Session '
        f'({remaining} slot{"s" if remaining > 1 else ""} remaining)</p>',
        unsafe_allow_html=True,
    )

    team_robot_slots = {b["slot_label"] for b in robot_bookings}

    selected_room = st.selectbox(
        "Choose a robot (by room)",
        options=SCHED_ROBOT_ROOMS,
        format_func=lambda r: f"Robot in {r}",
        key="sched_robot_pick",
    )

    def _avail_slots_for_robot(room):
        result = []
        for slot in SCHED_ALL_SLOTS:
            key = _robot_key(slot, room)
            if key not in robot_booked_map and slot not in team_robot_slots:
                result.append(slot)
        return result

    avail = _avail_slots_for_robot(selected_room)

    if not avail:
        st.warning(
            f"Robot in {selected_room} has no available slots "
            "(or you've already used those times). Try a different robot."
        )
    else:
        fri_options = [s for s in avail if _is_friday_slot(s)]
        sat_options = [s for s in avail if not _is_friday_slot(s)]

        display_options = []
        if fri_options:
            display_options += ["── Friday Mar 6 ──"] + fri_options
        if sat_options:
            display_options += ["── Saturday Mar 7 ──"] + sat_options

        raw_choice = st.selectbox(
            "Choose a time slot",
            options=display_options,
            key="sched_robot_slot",
        )

        is_separator = raw_choice.startswith("──")

        if not is_separator:
            if st.button("Book Robot Session", type="primary", use_container_width=True):
                try:
                    create_robot_booking(team_name, selected_room, raw_choice)
                    st.success(
                        f"🎉 Booked: **Robot in {selected_room}** at **{raw_choice}**"
                    )
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
        else:
            st.caption("Select a specific time slot (not a header).")

    # ── Availability overview ─────────────────────────────────────────────────
    st.divider()
    st.markdown('<p class="ah-section">Full Availability Overview</p>', unsafe_allow_html=True)
    _render_robot_grid(robot_booked_map, team_name)


# ── Main entry point ─────────────────────────────────────────────────────────────

def show():
    _render_header()

    st.markdown(
        "Book your **20-minute mentor sessions** and **robot demo sessions** for "
        "**Friday Mar 6** (6:20–8:00 PM) and **Saturday Mar 7** (10:00 AM–1:20 PM). "
        "Each team may book up to **2 mentor** and **2 robot** sessions. "
        "Only one team member needs to complete the booking."
    )
    st.divider()

    # ── Step 1: Team selection ────────────────────────────────────────────────
    st.markdown('<p class="ah-section">Step 1 — Select Your Team</p>', unsafe_allow_html=True)

    st.markdown(
        '<p style="color:rgba(180,195,225,0.60);font-size:0.83rem;margin-bottom:10px;">'
        'If your team name is not in the list below, please email '
        '<a href="mailto:Shubhneet.Sandhu@GeorgianCollege.ca" style="color:#6B9FE4;">'
        'Shubhneet.Sandhu@GeorgianCollege.ca</a> or '
        '<a href="mailto:Brunilda.Xhaferllari@GeorgianCollege.ca" style="color:#6B9FE4;">'
        'Brunilda.Xhaferllari@GeorgianCollege.ca</a>.'
        '</p>',
        unsafe_allow_html=True,
    )

    team_names = get_bookable_team_names()
    selected_team = st.selectbox(
        "team_select",
        options=["— Select your team —"] + team_names,
        label_visibility="collapsed",
        key="sched_team_select",
    )

    if selected_team == "— Select your team —":
        return

    # ── Step 2: Team details ──────────────────────────────────────────────────
    st.divider()
    st.markdown(
        '<p class="ah-section">Step 2 — Confirm Your Team Details</p>',
        unsafe_allow_html=True,
    )

    reg = _get_reg_for_team(selected_team)
    if not reg:
        st.error(
            "Could not find registration details for this team. "
            "Please contact the organizers."
        )
        return

    members_html = ""
    for m in reg.get("members", []):
        members_html += (
            f'<p style="margin:2px 0;color:rgba(210,220,245,0.85);font-size:0.88rem;">'
            f'• {m.get("name","—")} &nbsp;·&nbsp; {m.get("email","—")}</p>'
        )

    st.markdown(
        f'<div class="ah-info-card">'
        f'  <p class="ah-info-label">Team Name</p>'
        f'  <p style="font-size:1.1rem;font-weight:700;color:#FFFFFF;margin:0 0 10px;">'
        f'{reg["team_name"]}</p>'
        f'  <p class="ah-info-label">Project</p>'
        f'  <p style="margin:0 0 10px;">{reg.get("project_name","—")}</p>'
        f'  <p class="ah-info-label">Members</p>'
        f'  {members_html}'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Step 3: Booking tabs ──────────────────────────────────────────────────
    st.divider()
    st.markdown(
        '<p class="ah-section">Step 3 — Book Your Sessions</p>',
        unsafe_allow_html=True,
    )

    tab_mentor, tab_robot = st.tabs(
        ["\U0001f9d1\u200d\U0001f3eb Mentor Sessions", "\U0001f916 Robot Sessions"]
    )

    with tab_mentor:
        _mentor_tab(selected_team)

    with tab_robot:
        _robot_tab(selected_team)

    st.divider()
    st.caption(
        "Having trouble? Contact us at "
        "[Shubhneet.Sandhu@GeorgianCollege.ca](mailto:Shubhneet.Sandhu@GeorgianCollege.ca) "
        "or "
        "[Brunilda.Xhaferllari@GeorgianCollege.ca](mailto:Brunilda.Xhaferllari@GeorgianCollege.ca)."
    )
