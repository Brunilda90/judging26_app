"""
views/booking_page.py

Public-facing prelim booking portal.
Accessible via ?page=book (no login required).
Teams select a 10-minute slot in one of 3 rooms for the prelims judging round.
"""

import os
import base64
import streamlit as st

from db import (
    PRELIM_ROOMS,
    PRELIM_SLOTS,
    get_bookable_team_names,
    get_booking_by_team_name,
    get_booked_slot_map,
    get_team_registrations,
    create_booking,
    switch_booking,
)

# ── Asset paths ─────────────────────────────────────────────────────────────────
_LOGO_AH_SVG    = os.path.join("assets", "autohack_logo.svg")
_LOGO_AH_PNG    = os.path.join("assets", "autohack_logo.png")
_LOGO_AH_WHITE  = os.path.join("assets", "autohack_logo_white.png")
_LOGO_GC_PNG    = os.path.join("assets", "georgian_logo.png")

# ── Background: dark automotive / tire-track overlay ────────────────────────────
_BG_URL = (
    "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7"
    "?auto=format&fit=crop&w=1920&q=80"
)

# ── CSS ─────────────────────────────────────────────────────────────────────────
_CSS = f"""
<style>
/* Full-page dark automotive background */
.stApp {{
    background-image:
        linear-gradient(rgba(0,0,0,0.82), rgba(0,0,0,0.88)),
        url('{_BG_URL}');
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
    min-height: 100vh;
}}

/* Glassmorphism content panel */
.main .block-container {{
    background: rgba(10, 12, 22, 0.68) !important;
    backdrop-filter: blur(18px) !important;
    -webkit-backdrop-filter: blur(18px) !important;
    border-radius: 20px !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    padding: 2.5rem 3rem !important;
    max-width: 980px !important;
    margin-top: 1.5rem !important;
    margin-bottom: 2rem !important;
    box-shadow: 0 8px 60px rgba(0,0,0,0.60) !important;
}}

/* Section labels */
.ah-section {{
    color: #FF4040; font-weight: 700; font-size: 0.80rem;
    text-transform: uppercase; letter-spacing: 1.4px;
    border-left: 3px solid #CC0000; padding: 2px 0 2px 10px; margin: 6px 0 12px;
}}

/* Subtitle stripe */
.ah-subtitle {{
    color: rgba(200,210,230,0.70); font-size: 0.95rem;
    letter-spacing: 2.5px; text-transform: uppercase; font-weight: 300; margin: 0;
}}
.ah-stripe {{
    height: 3px;
    background: linear-gradient(90deg, #CC0000 50%, #4A80D4 50%);
    border-radius: 2px; width: 55%; margin: 16px auto 0;
}}

/* Info card */
.ah-info-card {{
    background: rgba(26,75,153,0.15);
    border: 1px solid rgba(74,128,212,0.35);
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 12px;
}}
.ah-info-card p {{ color: rgba(220,230,250,0.90) !important; margin: 4px 0 !important; }}
.ah-info-label {{ color: #6B9FE4 !important; font-weight: 600 !important; font-size: 0.82rem !important; text-transform: uppercase; letter-spacing: 0.8px; }}

/* Booking confirmation card */
.ah-booking-card {{
    background: linear-gradient(135deg, rgba(20,60,140,0.30) 0%, rgba(10,12,22,0.85) 100%);
    border: 1px solid rgba(74,128,212,0.55);
    border-radius: 14px;
    padding: 20px 24px;
    margin-bottom: 16px;
    text-align: center;
}}
.ah-booking-card h3 {{ color: #FFFFFF; margin: 0 0 6px; font-size: 1.4rem; font-weight: 800; }}
.ah-booking-card p  {{ color: rgba(220,230,250,0.85); margin: 0; font-size: 1.05rem; }}

/* Slot grid cells */
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

/* All general text → white */
.stMarkdown p, .stMarkdown li, .stMarkdown strong, .stMarkdown em {{
    color: rgba(225,230,245,0.90) !important;
}}
label, .stRadio label {{ color: rgba(220,228,245,0.90) !important; }}

/* Selectbox / inputs */
[data-baseweb="base-input"], [data-baseweb="textarea"] {{
    background: rgba(18, 20, 40, 0.92) !important;
    border: 1px solid rgba(255,255,255,0.16) !important;
    border-radius: 8px !important;
}}
[data-baseweb="base-input"] input, [data-baseweb="textarea"] textarea {{
    background: transparent !important;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
}}

/* Primary button → Honda Red */
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

hr {{ border-color: rgba(255,255,255,0.10) !important; }}
</style>
"""


# ── Helpers ──────────────────────────────────────────────────────────────────────

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

    # Try white logo first (better on dark), fall back to coloured versions
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
        '  <p class="ah-subtitle">Prelims Slot Booking</p>'
        '  <div class="ah-stripe"></div>'
        '</div>'
    )

    st.markdown(banner + subtitle, unsafe_allow_html=True)


def _get_reg_for_team(team_name: str):
    """Return the registration document for a team name, or None."""
    # Search across all non-rejected statuses so pending teams are found too
    for status in ("pending", "approved"):
        regs = get_team_registrations(status=status)
        for r in regs:
            if r["team_name"] == team_name:
                return r
    return None


def _slot_key(slot_label: str, room: str) -> str:
    return f"{slot_label}||{room}"


# ── Booking grid renderer ────────────────────────────────────────────────────────

def _render_grid(booked_map: dict, my_team: str):
    """Show the full 9×3 grid as a read-only summary."""
    # Header row
    cols = st.columns([2.0] + [1.0] * len(PRELIM_ROOMS))
    cols[0].markdown(f'<p style="color:#6B9FE4;font-weight:700;font-size:0.82rem;text-transform:uppercase;padding-bottom:4px;border-bottom:1px solid rgba(74,128,212,0.35);">Time Slot</p>', unsafe_allow_html=True)
    for i, room in enumerate(PRELIM_ROOMS, start=1):
        cols[i].markdown(f'<p style="color:#6B9FE4;font-weight:700;font-size:0.82rem;text-transform:uppercase;text-align:center;padding-bottom:4px;border-bottom:1px solid rgba(74,128,212,0.35);">Room {room}</p>', unsafe_allow_html=True)

    for slot in PRELIM_SLOTS:
        row = st.columns([2.0] + [1.0] * len(PRELIM_ROOMS))
        row[0].markdown(f'<p style="color:rgba(220,230,250,0.85);font-size:0.88rem;padding-top:6px;">{slot}</p>', unsafe_allow_html=True)
        for i, room in enumerate(PRELIM_ROOMS, start=1):
            key = _slot_key(slot, room)
            occupant = booked_map.get(key)
            if occupant and occupant == my_team:
                row[i].markdown(f'<div class="slot-mine">⭐ You</div>', unsafe_allow_html=True)
            elif occupant:
                row[i].markdown(f'<div class="slot-taken">Taken</div>', unsafe_allow_html=True)
            else:
                row[i].markdown(f'<div class="slot-free">Free</div>', unsafe_allow_html=True)


# ── Slot picker ──────────────────────────────────────────────────────────────────

def _render_slot_picker(booked_map: dict, label: str = "Select a time slot") -> tuple:
    """Let user pick an available (slot, room) combination. Returns (slot, room) or (None, None)."""
    # Build list of available options
    options = []
    for slot in PRELIM_SLOTS:
        for room in PRELIM_ROOMS:
            key = _slot_key(slot, room)
            if key not in booked_map:
                options.append(f"{slot}  —  Room {room}")

    if not options:
        st.warning("⚠️ No slots are currently available. Please contact the organizers.")
        return None, None

    st.markdown(f'<p class="ah-section">{label}</p>', unsafe_allow_html=True)
    choice = st.selectbox(
        "slot_picker",
        options=options,
        label_visibility="collapsed",
        key="booking_slot_select",
    )
    if not choice:
        return None, None

    # Parse choice back to (slot_label, room)
    # Format: "2:00 PM – 2:10 PM  —  Room N200"
    parts = choice.split("  —  Room ")
    if len(parts) != 2:
        return None, None
    return parts[0].strip(), parts[1].strip()


# ── Main entry point ─────────────────────────────────────────────────────────────

def show():
    _render_header()

    st.markdown(
        "Welcome to the **AutoHack 2026 Prelims Booking Portal**. "
        "Select your team and pick a 10-minute judging slot between **2:00 PM and 3:30 PM**. "
        "**Only one team member needs to complete this booking on behalf of the group.**"
    )
    st.divider()

    # ── Step 1: Team selection ───────────────────────────────────────────────────
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
        key="booking_team_select",
    )

    if selected_team == "— Select your team —":
        return

    # ── Step 2: Team info confirmation ───────────────────────────────────────────
    st.divider()
    st.markdown('<p class="ah-section">Step 2 — Confirm Your Team Details</p>', unsafe_allow_html=True)

    reg = _get_reg_for_team(selected_team)
    if not reg:
        st.error("Could not find registration details for this team. Please contact the organizers.")
        return

    # Display team info card
    members_html = ""
    for m in reg.get("members", []):
        members_html += f'<p style="margin:2px 0;color:rgba(210,220,245,0.85);font-size:0.88rem;">• {m.get("name","—")} &nbsp;·&nbsp; {m.get("email","—")}</p>'

    st.markdown(
        f'<div class="ah-info-card">'
        f'  <p class="ah-info-label">Team Name</p>'
        f'  <p style="font-size:1.1rem;font-weight:700;color:#FFFFFF;margin:0 0 10px;">{reg["team_name"]}</p>'
        f'  <p class="ah-info-label">Project</p>'
        f'  <p style="margin:0 0 10px;">{reg.get("project_name","—")}</p>'
        f'  <p class="ah-info-label">Members</p>'
        f'  {members_html}'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Check for existing booking ───────────────────────────────────────────────
    existing = get_booking_by_team_name(selected_team)
    booked_map = get_booked_slot_map()

    if existing:
        st.success(
            f"✅ Your team is already booked for **{existing['slot_label']}** in **Room {existing['room']}**."
        )
        st.markdown(
            f'<div class="ah-booking-card">'
            f'  <h3>📍 Your Slot</h3>'
            f'  <p>{existing["slot_label"]}  &nbsp;·&nbsp;  Room {existing["room"]}</p>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Slot overview
        st.divider()
        st.markdown('<p class="ah-section">Current Availability</p>', unsafe_allow_html=True)
        _render_grid(booked_map, selected_team)

        # Switch option
        st.divider()
        st.markdown('<p class="ah-section">Step 3 — Switch Your Slot (optional)</p>', unsafe_allow_html=True)
        st.write("If you need a different time, select a new slot below and confirm.")

        # Remove existing slot from booked_map so it doesn't show as "taken" for the picker
        freed_map = {k: v for k, v in booked_map.items() if v != selected_team}

        new_slot, new_room = _render_slot_picker(freed_map, "Choose a new time slot")

        if new_slot and new_room:
            if st.button("Switch Slot", type="primary", use_container_width=True):
                try:
                    switch_booking(selected_team, new_slot, new_room)
                    st.success(f"✅ Slot switched to **{new_slot}** — Room **{new_room}**!")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))

    else:
        # No booking yet — show availability and let them book
        st.divider()
        st.markdown('<p class="ah-section">Step 3 — Book Your Slot</p>', unsafe_allow_html=True)
        st.write("Below is the current availability. Green = free, Red = taken.")

        _render_grid(booked_map, selected_team)

        st.divider()
        new_slot, new_room = _render_slot_picker(booked_map, "Choose your time slot")

        if new_slot and new_room:
            if st.button("Confirm Booking", type="primary", use_container_width=True):
                try:
                    create_booking(selected_team, new_slot, new_room)
                    st.success(f"🎉 Booking confirmed! **{new_slot}** — Room **{new_room}**")
                    st.balloons()
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))

    st.divider()
    st.caption(
        "Having trouble? Contact us at "
        "[Shubhneet.Sandhu@GeorgianCollege.ca](mailto:Shubhneet.Sandhu@GeorgianCollege.ca) "
        "or "
        "[Brunilda.Xhaferllari@GeorgianCollege.ca](mailto:Brunilda.Xhaferllari@GeorgianCollege.ca)."
    )
