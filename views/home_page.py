"""
views/home_page.py

Main landing page — four portal cards for easy navigation.
Accessible at the root URL (no login required).
"""

import os
import base64
import streamlit as st

# ── Asset paths ─────────────────────────────────────────────────────────────────
_LOGO_AH_SVG   = os.path.join("assets", "autohack_logo.svg")
_LOGO_AH_PNG   = os.path.join("assets", "autohack_logo.png")
_LOGO_AH_WHITE = os.path.join("assets", "autohack_logo_white.png")
_LOGO_GC_PNG   = os.path.join("assets", "georgian_logo.png")

# Dark automotive background (tyre/road)
_BG_URL = (
    "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7"
    "?auto=format&fit=crop&w=1920&q=80"
)

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
    max-width: 1020px !important;
    margin-top: 1.5rem !important;
    margin-bottom: 2rem !important;
    box-shadow: 0 8px 60px rgba(0,0,0,0.60) !important;
}}

/* Subtitle / stripe */
.ah-subtitle {{
    color: rgba(200,210,230,0.70); font-size: 0.95rem;
    letter-spacing: 2.5px; text-transform: uppercase; font-weight: 300; margin: 0;
}}
.ah-stripe {{
    height: 3px;
    background: linear-gradient(90deg, #CC0000 50%, #4A80D4 50%);
    border-radius: 2px; width: 55%; margin: 16px auto 0;
}}

/* ── Portal cards ── */
.portal-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin-top: 32px;
}}

.portal-card {{
    display: block;
    text-decoration: none !important;
    border-radius: 16px;
    padding: 32px 28px;
    transition: transform 0.18s ease, box-shadow 0.18s ease;
    cursor: pointer;
    position: relative;
    overflow: hidden;
}}
.portal-card:hover {{
    transform: translateY(-4px);
    text-decoration: none !important;
}}

/* Registration — red accent */
.card-register {{
    background: linear-gradient(135deg, rgba(140,0,0,0.55) 0%, rgba(10,12,22,0.85) 100%);
    border: 1px solid rgba(204,0,0,0.55);
    box-shadow: 0 4px 30px rgba(204,0,0,0.20);
}}
.card-register:hover {{
    box-shadow: 0 8px 48px rgba(204,0,0,0.40);
    border-color: rgba(204,0,0,0.80);
}}

/* Booking — blue accent */
.card-booking {{
    background: linear-gradient(135deg, rgba(20,60,140,0.55) 0%, rgba(10,12,22,0.85) 100%);
    border: 1px solid rgba(74,128,212,0.55);
    box-shadow: 0 4px 30px rgba(74,128,212,0.20);
}}
.card-booking:hover {{
    box-shadow: 0 8px 48px rgba(74,128,212,0.40);
    border-color: rgba(74,128,212,0.80);
}}

/* Admin — teal/dark accent */
.card-admin {{
    background: linear-gradient(135deg, rgba(0,100,80,0.45) 0%, rgba(10,12,22,0.85) 100%);
    border: 1px solid rgba(0,180,140,0.40);
    box-shadow: 0 4px 30px rgba(0,180,140,0.12);
}}
.card-admin:hover {{
    box-shadow: 0 8px 48px rgba(0,180,140,0.30);
    border-color: rgba(0,200,160,0.70);
}}

/* Judge — purple/dark accent */
.card-judge {{
    background: linear-gradient(135deg, rgba(80,20,120,0.45) 0%, rgba(10,12,22,0.85) 100%);
    border: 1px solid rgba(160,80,220,0.40);
    box-shadow: 0 4px 30px rgba(160,80,220,0.12);
}}
.card-judge:hover {{
    box-shadow: 0 8px 48px rgba(160,80,220,0.30);
    border-color: rgba(180,100,240,0.70);
}}

/* Scheduling — amber/gold accent */
.card-schedule {{
    background: linear-gradient(135deg, rgba(120,80,0,0.50) 0%, rgba(10,12,22,0.85) 100%);
    border: 1px solid rgba(220,160,0,0.45);
    box-shadow: 0 4px 30px rgba(220,160,0,0.15);
}}
.card-schedule:hover {{
    box-shadow: 0 8px 48px rgba(220,160,0,0.35);
    border-color: rgba(240,180,0,0.75);
}}

/* Mentor schedule view — cyan/teal accent */
.card-mentor-view {{
    background: linear-gradient(135deg, rgba(0,100,130,0.50) 0%, rgba(10,12,22,0.85) 100%);
    border: 1px solid rgba(0,180,220,0.40);
    box-shadow: 0 4px 30px rgba(0,180,220,0.12);
}}
.card-mentor-view:hover {{
    box-shadow: 0 8px 48px rgba(0,180,220,0.30);
    border-color: rgba(0,200,240,0.70);
}}

.card-icon {{
    font-size: 2.6rem;
    display: block;
    margin-bottom: 14px;
    line-height: 1;
}}
.card-title {{
    color: #FFFFFF;
    font-size: 1.25rem;
    font-weight: 800;
    letter-spacing: 0.4px;
    margin: 0 0 8px;
    display: block;
}}
.card-desc {{
    color: rgba(200,215,240,0.70);
    font-size: 0.88rem;
    line-height: 1.55;
    margin: 0;
    display: block;
}}
.card-arrow {{
    position: absolute;
    bottom: 20px;
    right: 22px;
    font-size: 1.3rem;
    opacity: 0.40;
    transition: opacity 0.18s ease, right 0.18s ease;
}}
.portal-card:hover .card-arrow {{
    opacity: 0.85;
    right: 16px;
}}

/* All general text → white */
.stMarkdown p {{ color: rgba(225,230,245,0.85) !important; }}
hr {{ border-color: rgba(255,255,255,0.10) !important; }}
</style>
"""


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
                 "width:100%;max-width:600px;height:auto;object-fit:contain;",
                 "AutoHack 2026")
        or _b64_tag(_LOGO_AH_SVG,
                    "width:100%;max-width:600px;height:auto;object-fit:contain;",
                    "AutoHack 2026")
        or _b64_tag(_LOGO_AH_PNG,
                    "width:100%;max-width:600px;height:auto;object-fit:contain;",
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
        '  <p class="ah-subtitle">Georgian College Hackathon — Feb 28, 2026</p>'
        '  <div class="ah-stripe"></div>'
        '</div>'
    )

    st.markdown(banner + subtitle, unsafe_allow_html=True)


def show():
    _render_header()

    st.markdown(
        '<p style="text-align:center;color:rgba(200,215,240,0.70);'
        'font-size:1.0rem;margin:20px 0 0;">Select your portal below to get started.</p>',
        unsafe_allow_html=True,
    )

    cards_html = """
    <div class="portal-grid">

      <a href="/?page=register" class="portal-card card-register">
        <span class="card-icon">📝</span>
        <span class="card-title">Team Registration</span>
        <span class="card-desc">
          Register your team for AutoHack 2026.<br>
          One submission per team needed.
        </span>
        <span class="card-arrow">→</span>
      </a>

      <a href="/?page=book" class="portal-card card-booking">
        <span class="card-icon">📅</span>
        <span class="card-title">Prelims Slot Booking</span>
        <span class="card-desc">
          Book your 10-minute demo slot for the<br>
          prelims round (2:00 PM – 3:30 PM).
        </span>
        <span class="card-arrow">→</span>
      </a>

      <a href="/?page=login" class="portal-card card-admin">
        <span class="card-icon">⚙️</span>
        <span class="card-title">Admin Portal</span>
        <span class="card-desc">
          Event organizers: manage registrations,<br>
          bookings, judges, and competitors.
        </span>
        <span class="card-arrow">→</span>
      </a>

      <a href="/?page=login" class="portal-card card-judge">
        <span class="card-icon">⚖️</span>
        <span class="card-title">Judge Portal</span>
        <span class="card-desc">
          Competition judges: log in to enter<br>
          scores for competing teams.
        </span>
        <span class="card-arrow">→</span>
      </a>

      <a href="/?page=schedule" class="portal-card card-schedule">
        <span class="card-icon">🗓️</span>
        <span class="card-title">Mentor &amp; Robot Schedule</span>
        <span class="card-desc">
          Book 20-min mentor sessions and robot demo slots for
          Friday Mar 6 (6:20–8:00 PM) &amp; Saturday Mar 7 (10:00 AM–1:20 PM).
        </span>
        <span class="card-arrow">→</span>
      </a>

      <a href="/?page=mentor_schedule" class="portal-card card-mentor-view">
        <span class="card-icon">📋</span>
        <span class="card-title">Mentor Schedule View</span>
        <span class="card-desc">
          Mentors: see which teams have booked
          sessions in your room and when.
        </span>
        <span class="card-arrow">→</span>
      </a>

    </div>
    """

    st.markdown(cards_html, unsafe_allow_html=True)

    st.markdown(
        '<p style="text-align:center;color:rgba(180,190,215,0.40);'
        'font-size:0.78rem;margin-top:40px;">'
        'Need help? Contact '
        '<a href="mailto:Shubhneet.Sandhu@GeorgianCollege.ca" '
        'style="color:rgba(107,159,228,0.70);">Shubhneet.Sandhu@GeorgianCollege.ca</a>'
        '</p>',
        unsafe_allow_html=True,
    )
