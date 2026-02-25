"""
views/scheduling_page.py

Public-facing mentor & robot scheduling portal.
Accessible via ?page=schedule (no login required).

Teams enter their registration email to look up their team, confirm with a
checkbox, then book up to 2 mentor sessions and up to 2 robot demo sessions
across two time windows:
  - Friday  Mar 6, 2026  6:20 PM – 8:00 PM  (5 × 20-min slots)
  - Saturday Mar 7, 2026 10:00 AM – 1:20 PM (10 × 20-min slots)
"""

import os
import base64
import streamlit as st

from db import (
    MENTOR_NAMES,
    MENTOR_ROOM_MAP,
    SCHED_ROBOT_ROOMS,
    SCHED_FRIDAY_SLOTS,
    SCHED_SATURDAY_SLOTS,
    SCHED_ALL_SLOTS,
    MAX_MENTOR_BOOKINGS,
    MAX_ROBOT_BOOKINGS,
    get_team_by_member_email,
    get_mentor_bookings_for_team,
    get_robot_bookings_for_team,
    get_mentor_booked_map,
    get_robot_booked_map,
    create_mentor_booking_room,
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
    border-radius: 8px; padding: 6px 10px; text-align: center;
    color: rgba(255,160,160,0.85); font-size: 0.82rem; font-weight: 600;
    margin: 2px 0;
}}
.slot-mine {{
    background: rgba(26,75,153,0.55);
    border: 2px solid #4A80D4;
    border-radius: 8px; padding: 6px 10px; text-align: center;
    color: #FFFFFF; font-size: 0.82rem; font-weight: 700;
    margin: 2px 0;
}}
.slot-free {{
    background: rgba(40,100,40,0.25);
    border: 1px solid rgba(60,200,80,0.40);
    border-radius: 8px; padding: 6px 10px; text-align: center;
    color: rgba(120,240,140,0.90); font-size: 0.82rem; font-weight: 600;
    margin: 2px 0;
}}

/* Tabs — make labels clearly readable on dark background */
.stTabs [data-baseweb="tab-list"] {{
    background-color: rgba(12, 15, 30, 0.65) !important;
    border-radius: 10px !important;
    padding: 4px !important;
    gap: 4px !important;
}}
.stTabs button[role="tab"] {{
    color: rgba(210, 225, 250, 0.90) !important;
    font-size: 0.96rem !important;
    font-weight: 600 !important;
    border-radius: 7px !important;
    padding: 6px 18px !important;
}}
.stTabs button[role="tab"][aria-selected="true"] {{
    color: #FFFFFF !important;
    font-weight: 700 !important;
    background-color: rgba(204, 0, 0, 0.18) !important;
}}
.stTabs [data-baseweb="tab-highlight"] {{
    background-color: #CC0000 !important;
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


# ── Slot key helpers ─────────────────────────────────────────────────────────────

def _is_friday_slot(slot_label: str) -> bool:
    return slot_label.startswith("Fri")


def _short(slot_label: str) -> str:
    """Strip the day prefix, e.g. 'Fri Mar 6 · 6:20 – 6:40 PM' → '6:20 – 6:40 PM'."""
    return slot_label.split("\u00b7", 1)[-1].strip()


# ── Availability grids ────────────────────────────────────────────────────────────

def _mentor_rooms_ordered() -> list:
    """Distinct rooms from MENTOR_ROOM_MAP in insertion order."""
    return list(dict.fromkeys(MENTOR_ROOM_MAP.values()))


def _render_mentor_grid(mentor_booked_map: dict, my_team: str):
    """Mentor availability grid — identical format to the robot/prelims grid.
    Rows = time slots.  Columns = Rooms (N200, N217, N300A).
    A cell is ⭐ You if the team has a booking in that room at that slot,
    Full if all mentors in the room are taken, or Free otherwise.
    """
    rooms = _mentor_rooms_ordered()
    mentors_per_room = {r: [m for m, rm in MENTOR_ROOM_MAP.items() if rm == r] for r in rooms}
    col_widths = [2.0] + [1.0] * len(rooms)

    # Header row
    hcols = st.columns(col_widths)
    hcols[0].markdown(
        '<p style="color:#6B9FE4;font-weight:700;font-size:0.82rem;'
        'text-transform:uppercase;padding-bottom:4px;'
        'border-bottom:1px solid rgba(74,128,212,0.35);">Time Slot</p>',
        unsafe_allow_html=True,
    )
    for i, room in enumerate(rooms, start=1):
        hcols[i].markdown(
            f'<p style="color:#6B9FE4;font-weight:700;font-size:0.82rem;'
            f'text-transform:uppercase;text-align:center;padding-bottom:4px;'
            f'border-bottom:1px solid rgba(74,128,212,0.35);">Room {room}</p>',
            unsafe_allow_html=True,
        )

    last_day = None
    for slot in SCHED_ALL_SLOTS:
        day = "Friday Mar 6" if _is_friday_slot(slot) else "Saturday Mar 7"
        if day != last_day:
            last_day = day
            st.markdown(
                f"<p style='color:rgba(220,160,0,0.80);font-size:0.78rem;"
                f"font-weight:700;margin:8px 0 2px;'>&#9654; {day}</p>",
                unsafe_allow_html=True,
            )
        row = st.columns(col_widths)
        row[0].markdown(
            f'<p style="color:rgba(220,230,250,0.85);font-size:0.88rem;'
            f'padding-top:6px;">{_short(slot)}</p>',
            unsafe_allow_html=True,
        )
        for i, room in enumerate(rooms, start=1):
            mentors = mentors_per_room[room]
            team_here = any(
                mentor_booked_map.get(f"{slot}||{m}") == my_team for m in mentors
            )
            all_taken = all(f"{slot}||{m}" in mentor_booked_map for m in mentors)
            if team_here:
                row[i].markdown('<div class="slot-mine">⭐ You</div>', unsafe_allow_html=True)
            elif all_taken:
                row[i].markdown('<div class="slot-taken">Full</div>', unsafe_allow_html=True)
            else:
                row[i].markdown('<div class="slot-free">Free</div>', unsafe_allow_html=True)


def _render_robot_grid(robot_booked_map: dict, my_team: str):
    """Robot availability grid — identical format to the prelims rooms grid.
    Rows = time slots.  Columns = Room N200 / N217 / N300A.
    """
    col_widths = [2.0] + [1.0] * len(SCHED_ROBOT_ROOMS)

    # Header row
    hcols = st.columns(col_widths)
    hcols[0].markdown(
        '<p style="color:#6B9FE4;font-weight:700;font-size:0.82rem;'
        'text-transform:uppercase;padding-bottom:4px;'
        'border-bottom:1px solid rgba(74,128,212,0.35);">Time Slot</p>',
        unsafe_allow_html=True,
    )
    for i, room in enumerate(SCHED_ROBOT_ROOMS, start=1):
        hcols[i].markdown(
            f'<p style="color:#6B9FE4;font-weight:700;font-size:0.82rem;'
            f'text-transform:uppercase;text-align:center;padding-bottom:4px;'
            f'border-bottom:1px solid rgba(74,128,212,0.35);">Room {room}</p>',
            unsafe_allow_html=True,
        )

    last_day = None
    for slot in SCHED_ALL_SLOTS:
        day = "Friday Mar 6" if _is_friday_slot(slot) else "Saturday Mar 7"
        if day != last_day:
            last_day = day
            st.markdown(
                f"<p style='color:rgba(220,160,0,0.80);font-size:0.78rem;"
                f"font-weight:700;margin:8px 0 2px;'>&#9654; {day}</p>",
                unsafe_allow_html=True,
            )
        row = st.columns(col_widths)
        row[0].markdown(
            f'<p style="color:rgba(220,230,250,0.85);font-size:0.88rem;'
            f'padding-top:6px;">{_short(slot)}</p>',
            unsafe_allow_html=True,
        )
        for i, room in enumerate(SCHED_ROBOT_ROOMS, start=1):
            occupant = robot_booked_map.get(f"{slot}||{room}")
            if occupant and occupant == my_team:
                row[i].markdown('<div class="slot-mine">⭐ You</div>', unsafe_allow_html=True)
            elif occupant:
                row[i].markdown('<div class="slot-taken">Taken</div>', unsafe_allow_html=True)
            else:
                row[i].markdown('<div class="slot-free">Free</div>', unsafe_allow_html=True)


# ── Slot pickers ─────────────────────────────────────────────────────────────────

def _mentor_slot_picker(mentor_booked_map: dict, team_booked_slots: set):
    """Dropdown of available mentor slot + room combos — same format as robot picker.
    Returns (slot_label, room) or (None, None)."""
    rooms = _mentor_rooms_ordered()
    mentors_per_room = {r: [m for m, rm in MENTOR_ROOM_MAP.items() if rm == r] for r in rooms}

    options = []  # list of (display_label, slot_label, room)
    for slot in SCHED_ALL_SLOTS:
        if slot in team_booked_slots:
            continue
        for room in rooms:
            mentors = mentors_per_room[room]
            if any(f"{slot}||{m}" not in mentor_booked_map for m in mentors):
                day = "Fri" if _is_friday_slot(slot) else "Sat"
                options.append((f"{_short(slot)}  —  Room {room}  ({day})", slot, room))

    if not options:
        st.warning("⚠️ No mentor sessions are currently available. Please contact the organizers.")
        return None, None

    choice = st.selectbox(
        "mentor_slot_pick",
        options=[o[0] for o in options],
        label_visibility="collapsed",
        key="sched_mentor_slot_pick",
    )
    for label, slot, room in options:
        if label == choice:
            return slot, room
    return None, None


def _robot_slot_picker(robot_booked_map: dict, team_booked_slots: set):
    """Dropdown of available slot + room combos (like prelims). Returns (slot_label, room) or (None, None)."""
    options = []  # list of (display_label, slot_label, room)
    for slot in SCHED_ALL_SLOTS:
        if slot in team_booked_slots:
            continue
        for room in SCHED_ROBOT_ROOMS:
            if f"{slot}||{room}" not in robot_booked_map:
                day = "Fri" if _is_friday_slot(slot) else "Sat"
                options.append((f"{_short(slot)}  —  Room {room}  ({day})", slot, room))

    if not options:
        st.warning("⚠️ No robot sessions are currently available. Please contact the organizers.")
        return None, None

    choice = st.selectbox(
        "robot_slot_pick",
        options=[o[0] for o in options],
        label_visibility="collapsed",
        key="sched_robot_slot_pick",
    )
    for label, slot, room in options:
        if label == choice:
            return slot, room
    return None, None


# ── Mentor tab ───────────────────────────────────────────────────────────────────

def _mentor_tab(team_name: str):
    mentor_bookings   = get_mentor_bookings_for_team(team_name)
    mentor_booked_map = get_mentor_booked_map()
    slots_used        = len(mentor_bookings)
    team_booked_slots = {b["slot_label"] for b in mentor_bookings}

    # ── Friday encouragement ──────────────────────────────────────────────────
    has_friday = any(_is_friday_slot(b["slot_label"]) for b in mentor_bookings)
    if not has_friday and slots_used < MAX_MENTOR_BOOKINGS:
        st.warning(
            "⚠️ **Please prioritise a Friday evening session (6:20–8:00 PM)!** "
            "Getting mentor feedback on Friday gives you all of Saturday to apply it. "
            "Book a Friday slot below — it makes a big difference."
        )

    # ── Availability grid FIRST ───────────────────────────────────────────────
    st.markdown('<p class="ah-section">Availability Overview</p>', unsafe_allow_html=True)
    st.write("Green = free  ·  Full = all mentors in that room are taken  ·  ⭐ = your session")
    _render_mentor_grid(mentor_booked_map, team_name)

    st.divider()

    # ── Your current bookings ─────────────────────────────────────────────────
    st.markdown('<p class="ah-section">Your Mentor Sessions</p>', unsafe_allow_html=True)

    if mentor_bookings:
        for b in mentor_bookings:
            day_tag = "🟡 Friday" if _is_friday_slot(b["slot_label"]) else "🔵 Saturday"
            room = MENTOR_ROOM_MAP.get(b.get("mentor_name", ""), "—")
            st.markdown(
                f'<div class="ah-booking-card">'
                f'<p><strong>{_short(b["slot_label"])}</strong>'
                f'  &nbsp;·&nbsp;  Room {room}'
                f' &nbsp;<span style="opacity:0.60;font-size:0.78rem;">({day_tag})</span></p>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button(
                f"Cancel – {_short(b['slot_label'])} / Room {room}",
                key=f"cancel_mentor_{b['id']}",
            ):
                cancel_mentor_booking(b["id"])
                st.success("Mentor session cancelled.")
                st.rerun()
    else:
        st.info("No mentor sessions booked yet.")

    if slots_used >= MAX_MENTOR_BOOKINGS:
        st.success(
            f"✅ You've booked all {MAX_MENTOR_BOOKINGS} mentor sessions. "
            "Cancel one above if you need to change it."
        )
        return

    # ── Booking form ──────────────────────────────────────────────────────────
    remaining = MAX_MENTOR_BOOKINGS - slots_used
    st.divider()
    st.markdown(
        f'<p class="ah-section">Book a Mentor Session '
        f'({remaining} slot{"s" if remaining > 1 else ""} remaining)</p>',
        unsafe_allow_html=True,
    )

    chosen_slot, chosen_room = _mentor_slot_picker(mentor_booked_map, team_booked_slots)
    if chosen_slot and chosen_room:
        if st.button("Book Mentor Session", type="primary", use_container_width=True):
            try:
                create_mentor_booking_room(team_name, chosen_room, chosen_slot)
                st.success(
                    f"🎉 Mentor session booked for **{_short(chosen_slot)}** in **Room {chosen_room}**!"
                )
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))


# ── Robot tab ────────────────────────────────────────────────────────────────────

def _robot_tab(team_name: str):
    robot_bookings   = get_robot_bookings_for_team(team_name)
    robot_booked_map = get_robot_booked_map()
    slots_used       = len(robot_bookings)
    team_booked_slots = {b["slot_label"] for b in robot_bookings}

    st.info(
        f"🤖 Each team can book up to **{MAX_ROBOT_BOOKINGS}** robot demo sessions. "
        "Slots are shared across three rooms — pick any available time."
    )

    # ── Availability grid FIRST ───────────────────────────────────────────────
    st.markdown('<p class="ah-section">Availability Overview</p>', unsafe_allow_html=True)
    st.write("Green = free  ·  Red = taken  ·  ⭐ = your session")
    _render_robot_grid(robot_booked_map, team_name)

    st.divider()

    # ── Your current bookings ─────────────────────────────────────────────────
    st.markdown('<p class="ah-section">Your Robot Sessions</p>', unsafe_allow_html=True)

    if robot_bookings:
        for b in robot_bookings:
            day_tag = "🟡 Friday" if _is_friday_slot(b["slot_label"]) else "🔵 Saturday"
            st.markdown(
                f'<div class="ah-booking-card">'
                f'<p><strong>{_short(b["slot_label"])}</strong>'
                f'  &nbsp;·&nbsp;  Room {b["room"]}'
                f' &nbsp;<span style="opacity:0.60;font-size:0.78rem;">({day_tag})</span></p>'
                f'</div>',
                unsafe_allow_html=True,
            )
            short_slot = _short(b["slot_label"])
            if st.button(
                f"Cancel – {short_slot} / Room {b['room']}",
                key=f"cancel_robot_{b['id']}",
            ):
                cancel_robot_booking(b["id"])
                st.success("Robot session cancelled.")
                st.rerun()
    else:
        st.info("No robot sessions booked yet.")

    if slots_used >= MAX_ROBOT_BOOKINGS:
        st.success(
            f"✅ You've booked all {MAX_ROBOT_BOOKINGS} robot sessions. "
            "Cancel one above if you need to change it."
        )
        return

    # ── Booking form ──────────────────────────────────────────────────────────
    remaining = MAX_ROBOT_BOOKINGS - slots_used
    st.divider()
    st.markdown(
        f'<p class="ah-section">Book a Robot Session '
        f'({remaining} slot{"s" if remaining > 1 else ""} remaining)</p>',
        unsafe_allow_html=True,
    )

    chosen_slot, chosen_room = _robot_slot_picker(robot_booked_map, team_booked_slots)
    if chosen_slot and chosen_room:
        if st.button("Book Robot Session", type="primary", use_container_width=True):
            try:
                create_robot_booking(team_name, chosen_room, chosen_slot)
                st.success(
                    f"🎉 Robot session booked for **{_short(chosen_slot)}** — Room **{chosen_room}**!"
                )
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))


# ── Main entry point ─────────────────────────────────────────────────────────────

def show():
    _render_header()

    st.markdown(
        "Book your **20-minute mentor sessions** and **robot demo sessions** for "
        "**Friday Mar 6** (6:20–8:00 PM) and **Saturday Mar 7** (10:00 AM–1:20 PM). "
        "Each team may book up to **2 mentor** and **2 robot** sessions. "
        "Only one team member needs to complete the booking on behalf of the group."
    )
    st.divider()

    # ── Step 1: Email lookup ─────────────────────────────────────────────────────
    st.markdown(
        '<p class="ah-section">Step 1 — Enter Your Registration Email</p>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<p style="color:rgba(180,195,225,0.60);font-size:0.83rem;margin-bottom:10px;">'
        'Enter the email address you used when your team registered. '
        'If you have trouble, please email '
        '<a href="mailto:Shubhneet.Sandhu@GeorgianCollege.ca" style="color:#6B9FE4;">'
        'Shubhneet.Sandhu@GeorgianCollege.ca</a> or '
        '<a href="mailto:Brunilda.Xhaferllari@GeorgianCollege.ca" style="color:#6B9FE4;">'
        'Brunilda.Xhaferllari@GeorgianCollege.ca</a>.'
        '</p>',
        unsafe_allow_html=True,
    )

    email_raw = st.text_input(
        "sched_email",
        placeholder="your.email@example.com",
        label_visibility="collapsed",
        key="sched_email_input",
    )

    email = email_raw.strip().lower() if email_raw else ""
    if not email:
        return

    reg = get_team_by_member_email(email)
    if not reg:
        st.error(
            "⚠️ No registered team found for this email address. "
            "Please double-check for typos, or contact the organizers."
        )
        return

    # Reset confirmation checkbox when email changes
    if st.session_state.get("_sched_last_email") != email:
        st.session_state["sched_confirm_check"] = False
        st.session_state["_sched_last_email"] = email

    # ── Step 2: Confirm team details ─────────────────────────────────────────────
    st.divider()
    st.markdown(
        '<p class="ah-section">Step 2 — Confirm Your Team Details</p>',
        unsafe_allow_html=True,
    )

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

    confirmed = st.checkbox(
        "✅  Yes, this is my team — the information above is correct",
        key="sched_confirm_check",
    )
    if not confirmed:
        return

    selected_team = reg["team_name"]

    # ── Step 3: Booking tabs ──────────────────────────────────────────────────────
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
