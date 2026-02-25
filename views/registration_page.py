import os
import io
import base64
import streamlit as st
from datetime import datetime
from fpdf import FPDF
from db import register_team, team_name_exists, contact_email_registered

# ── Asset paths ────────────────────────────────────────────────────────────────
_LOGO_AH_WHITE = os.path.join("assets", "autohack_logo_white.png")
_LOGO_AH_SVG   = os.path.join("assets", "autohack_logo.svg")
_LOGO_AH_PNG   = os.path.join("assets", "autohack_logo.png")
_LOGO_GC_PNG   = os.path.join("assets", "georgian_logo.png")

# Background: dark sports-car photo (Unsplash, free to use)
_BG_URL = (
    "https://images.unsplash.com/photo-1494976388531-d1058494cdd8"
    "?auto=format&fit=crop&w=1920&q=80"
)

# ── CSS ────────────────────────────────────────────────────────────────────────
_CSS = f"""
<style>
/* Full-page dark automotive background */
.stApp {{
    background-image:
        linear-gradient(rgba(0,0,0,0.78), rgba(0,0,0,0.84)),
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

/* Hero title */
.ah-hero {{ text-align: center; padding: 8px 0 16px; }}
.ah-title {{
    font-size: 3.2rem; font-weight: 900; margin: 0 0 8px;
    letter-spacing: 3px; line-height: 1;
    text-shadow: 0 0 30px rgba(204,0,0,0.50), 0 0 60px rgba(26,75,153,0.35);
}}
.ah-auto  {{ color: #CC0000; }}
.ah-hack  {{ color: #4A80D4; }}
.ah-year  {{ color: #A0A8B8; font-size: 2rem; letter-spacing: 1px; }}
.ah-subtitle {{
    color: rgba(200,210,230,0.70); font-size: 0.95rem;
    letter-spacing: 2.5px; text-transform: uppercase; font-weight: 300; margin: 0;
}}
.ah-stripe {{
    height: 3px;
    background: linear-gradient(90deg, #CC0000 50%, #4A80D4 50%);
    border-radius: 2px; width: 55%; margin: 16px auto 0;
}}

/* Section labels */
.ah-section {{
    color: #FF4040; font-weight: 700; font-size: 0.80rem;
    text-transform: uppercase; letter-spacing: 1.4px;
    border-left: 3px solid #CC0000; padding: 2px 0 2px 10px; margin: 6px 0 12px;
}}

/* Member table headers */
.col-hdr {{
    font-weight: 600; color: #6B9FE4; font-size: 0.75rem;
    text-transform: uppercase; letter-spacing: 0.8px;
    padding-bottom: 5px; border-bottom: 1px solid rgba(74,128,212,0.35);
}}
.member-no {{
    color: #FF5555; font-weight: 700; font-size: 0.82rem;
    padding-top: 11px; display: block;
}}

/* Example row text */
.ah-example {{
    color: rgba(200,215,240,0.72);
    font-size: 0.92rem;
    margin: 2px 0 10px;
    font-style: italic;
}}

/* All general text → white */
.stMarkdown p, .stMarkdown li, .stMarkdown strong, .stMarkdown em {{
    color: rgba(225,230,245,0.90) !important;
}}
label, .stRadio label {{ color: rgba(220,228,245,0.90) !important; }}

/* Caption */
.stCaptionContainer p, [data-testid="stCaptionContainer"] p {{
    color: rgba(180,190,215,0.55) !important; font-size: 0.82rem !important;
}}

/* ── Input fix: dark background, white text ───────────────────── */
/* Target the BaseWeb container that wraps every input */
[data-baseweb="base-input"],
[data-baseweb="textarea"] {{
    background: rgba(18, 20, 40, 0.92) !important;
    border: 1px solid rgba(255,255,255,0.16) !important;
    border-radius: 8px !important;
}}
[data-baseweb="base-input"]:focus-within,
[data-baseweb="textarea"]:focus-within {{
    border-color: rgba(204,0,0,0.75) !important;
    box-shadow: 0 0 0 2px rgba(204,0,0,0.22) !important;
}}
/* The actual <input> / <textarea> inside */
[data-baseweb="base-input"] input,
[data-baseweb="textarea"] textarea {{
    background: transparent !important;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    caret-color: #CC0000;
}}
[data-baseweb="base-input"] input::placeholder,
[data-baseweb="textarea"] textarea::placeholder {{
    color: rgba(255,255,255,0.30) !important;
    -webkit-text-fill-color: rgba(255,255,255,0.30) !important;
}}

/* Radio */
.stRadio [data-testid="stMarkdownContainer"] p {{ color: rgba(220,228,245,0.90) !important; }}

/* Dividers */
hr {{ border-color: rgba(255,255,255,0.10) !important; }}

/* Primary button → Honda Red */
[data-testid="stBaseButton-primary"] {{
    background-color: #CC0000 !important; border-color: #CC0000 !important;
    color: white !important; font-weight: 700 !important; font-size: 0.95rem !important;
    letter-spacing: 0.8px !important; border-radius: 8px !important;
    text-transform: uppercase !important;
    box-shadow: 0 4px 24px rgba(204,0,0,0.45) !important;
    transition: all 0.18s ease !important;
}}
[data-testid="stBaseButton-primary"]:hover {{
    background-color: #EE1111 !important; border-color: #EE1111 !important;
    box-shadow: 0 6px 32px rgba(204,0,0,0.65) !important;
    transform: translateY(-1px) !important;
}}

/* Success card */
.ah-success {{
    background: linear-gradient(135deg, rgba(40,5,5,0.94) 0%, rgba(8,15,35,0.94) 100%);
    border-radius: 16px; padding: 36px 40px; text-align: center;
    border: 1px solid rgba(204,0,0,0.40);
    box-shadow: 0 0 50px rgba(204,0,0,0.18); margin-bottom: 24px;
}}
.ah-success h2 {{
    color: #FFFFFF; margin: 0 0 10px; font-size: 2rem; font-weight: 800; letter-spacing: 0.5px;
}}
.ah-success p {{ color: rgba(200,210,230,0.80); margin: 0; font-size: 1rem; line-height: 1.6; }}
</style>
"""


# ── Helpers ────────────────────────────────────────────────────────────────────

def _b64_tag(path: str, style: str, alt: str = "") -> str:
    """Read a local file and return a base64-embedded <img> tag."""
    if not os.path.exists(path):
        return ""
    ext  = os.path.splitext(path)[1].lstrip(".").lower()
    mime = "image/svg+xml" if ext == "svg" else f"image/{ext}"
    with open(path, "rb") as fh:
        b64 = base64.b64encode(fh.read()).decode()
    return f'<img src="data:{mime};base64,{b64}" style="{style}" alt="{alt}">'


def _render_header():
    st.markdown(_CSS, unsafe_allow_html=True)

    # ── AutoHack logo: large centered cover banner ─────────────────────────────
    ah_tag = (
        _b64_tag(_LOGO_AH_WHITE,
                 "width:100%;max-width:640px;height:auto;object-fit:contain;",
                 "AutoHack 2026")
        or _b64_tag(_LOGO_AH_SVG,
                    "width:100%;max-width:640px;height:auto;object-fit:contain;",
                    "AutoHack 2026")
        or _b64_tag(_LOGO_AH_PNG,
                    "width:100%;max-width:640px;height:auto;object-fit:contain;",
                    "AutoHack 2026")
    )

    # ── Georgian College logo: small, bottom-right of banner ───────────────────
    gc_tag = _b64_tag(
        _LOGO_GC_PNG,
        "height:48px;object-fit:contain;opacity:0.85;",
        "Georgian College"
    )

    # Banner wrapper: dark pill, full width, logo centred, GC logo bottom-right
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
        # GC logo pinned bottom-right inside the banner
        + (
            '<div style="position:absolute;bottom:14px;right:18px;">'
            f'{gc_tag}'
            '</div>'
            if gc_tag else ""
        ) +
        '</div>'
    )

    # Subtitle + racing stripe below the banner
    subtitle = (
        '<div class="ah-hero" style="padding-top:12px;">'
        '  <p class="ah-subtitle">Team Registration Form</p>'
        '  <div class="ah-stripe"></div>'
        '</div>'
    )

    st.markdown(banner + subtitle, unsafe_allow_html=True)


# ── PDF generation ─────────────────────────────────────────────────────────────

def _generate_pdf(team_name: str, members: list) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(14, 14, 14)

    # Title
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(204, 0, 0)
    pdf.cell(0, 12, "AutoHack 2026", ln=True, align="C")

    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(100, 100, 120)
    pdf.cell(0, 7, "Team Registration Confirmation", ln=True, align="C")

    # Red/blue divider line
    pdf.set_draw_color(204, 0, 0)
    pdf.set_line_width(0.8)
    pdf.line(14, pdf.get_y() + 3, 105, pdf.get_y() + 3)
    pdf.set_draw_color(74, 128, 212)
    pdf.line(105, pdf.get_y() + 3, 196, pdf.get_y() + 3)
    pdf.ln(8)

    # Team info
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(30, 30, 50)
    pdf.cell(38, 8, "Team Name:", ln=False)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, team_name, ln=True)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(38, 8, "Submitted:", ln=False)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"), ln=True)
    pdf.ln(4)

    # Members section heading
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(204, 0, 0)
    pdf.cell(0, 8, "Team Members", ln=True)
    pdf.ln(1)

    # Table header
    usable = 182  # mm
    col_w = [10, 44, 54, 40, 34]  # sums to 182
    headers = ["#", "Full Name", "Email", "Institution", "Program"]

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(255, 255, 255)
    pdf.set_fill_color(26, 75, 153)
    for w, h in zip(col_w, headers):
        pdf.cell(w, 8, h, border=1, fill=True, align="C")
    pdf.ln()

    # Table rows
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(20, 20, 40)
    for idx, m in enumerate(members, 1):
        fill = idx % 2 == 0
        pdf.set_fill_color(240, 243, 252) if fill else pdf.set_fill_color(255, 255, 255)
        row = [str(idx), m.get("name", ""), m.get("email", ""),
               m.get("institution", ""), m.get("program", "")]
        for w, val in zip(col_w, row):
            pdf.cell(w, 7, val[:28], border=1, fill=True)
        pdf.ln()

    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(150, 150, 170)
    pdf.cell(0, 6, "Generated by AutoHack 2026 Registration System", align="C")

    return bytes(pdf.output())


# ── Success screen ──────────────────────────────────────────────────────────────

def _render_success():
    team_name = st.session_state.get("submitted_team_name", "Your team")
    members   = st.session_state.get("submitted_members", [])

    st.markdown(
        f'<div class="ah-success">'
        f'  <h2>&#127937; Done!</h2>'
        f'  <p>'
        f'    Your team is now officially registered for AutoHack 2026 &#127950;<br><br>'
        f'    We\'ve got your details and we\'re stoked to have you in the race.<br><br>'
        f'    If you noticed an error in your submission or need to update any information, '
        f'    please email us at '
        f'    <a href="mailto:Shubhneet.Sandhu@GeorgianCollege.ca" '
        f'       style="color:#6B9FE4;">Shubhneet.Sandhu@GeorgianCollege.ca</a>'
        f'    &nbsp;or&nbsp;'
        f'    <a href="mailto:Brunilda.Xhaferllari@GeorgianCollege.ca" '
        f'       style="color:#6B9FE4;">Brunilda.Xhaferllari@GeorgianCollege.ca</a>.'
        f'  </p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    pdf_bytes = _generate_pdf(team_name, members)
    safe_name = team_name.replace(" ", "_").replace("/", "-")
    st.download_button(
        label="Download registration confirmation (PDF)",
        data=pdf_bytes,
        file_name=f"AutoHack2026_Registration_{safe_name}.pdf",
        mime="application/pdf",
        type="primary",
        use_container_width=True,
    )


# ── State helpers ───────────────────────────────────────────────────────────────

def _clear_form_state():
    keys = [
        "registration_submitted", "submitted_team_name", "submitted_members",
        "reg_team_name", "reg_team_size",
    ]
    for i in range(1, 7):
        keys += [f"reg_m_name_{i}", f"reg_m_email_{i}",
                 f"reg_m_inst_{i}", f"reg_m_prog_{i}"]
    for k in keys:
        st.session_state.pop(k, None)


# ── Member grid ─────────────────────────────────────────────────────────────────

def _collect_members(team_size: int) -> list:
    h0, h1, h2, h3, h4 = st.columns([1.1, 2.3, 2.5, 2.1, 2.3])
    h0.markdown('<p class="col-hdr">&nbsp;</p>',      unsafe_allow_html=True)
    h1.markdown('<p class="col-hdr">Full Name</p>',   unsafe_allow_html=True)
    h2.markdown('<p class="col-hdr">Email</p>',       unsafe_allow_html=True)
    h3.markdown('<p class="col-hdr">Institution</p>', unsafe_allow_html=True)
    h4.markdown('<p class="col-hdr">Program</p>',     unsafe_allow_html=True)

    members = []
    for i in range(1, team_size + 1):
        c0, c1, c2, c3, c4 = st.columns([1.1, 2.3, 2.5, 2.1, 2.3])
        c0.markdown(f'<span class="member-no">Member {i}</span>', unsafe_allow_html=True)
        name  = c1.text_input("n", key=f"reg_m_name_{i}", label_visibility="collapsed",
                               max_chars=80,  placeholder="Full Name")
        email = c2.text_input("e", key=f"reg_m_email_{i}", label_visibility="collapsed",
                               max_chars=120, placeholder="email@example.com")
        inst  = c3.text_input("i", key=f"reg_m_inst_{i}",  label_visibility="collapsed",
                               max_chars=120, placeholder="e.g. Georgian College")
        prog  = c4.text_input("p", key=f"reg_m_prog_{i}",  label_visibility="collapsed",
                               max_chars=120, placeholder="e.g. Computer Engineering Technology")
        members.append((name.strip(), email.strip(), inst.strip(), prog.strip()))
    return members


# ── Validation ──────────────────────────────────────────────────────────────────

def _validate(team_name, team_size, members):
    errors = []
    if not team_name.strip():
        errors.append("Team Name is required.")
    for i, (name, email, inst, prog) in enumerate(members[:team_size], start=1):
        if not name:
            errors.append(f"Member {i}: Full Name is required.")
        if not email or "@" not in email:
            errors.append(f"Member {i}: a valid Email is required.")
        if not inst:
            errors.append(f"Member {i}: Institution is required.")
        if not prog:
            errors.append(f"Member {i}: Program is required.")
    if not errors:
        if team_name_exists(team_name.strip()):
            errors.append("A team with this name is already registered. Please choose a different name.")
    return errors


# ── Main entry point ────────────────────────────────────────────────────────────

def show():
    _render_header()

    if st.session_state.get("registration_submitted"):
        _render_success()
        return

    st.markdown(
        "We're excited to have you join **AutoHack 2026!** "
        "Please fill out this form to register your team. Make sure all details are accurate "
        "before submitting. **Only one response per team is needed.** The team leader will serve "
        "as the main contact for competition updates. We can't wait to see what you build! ⚙️"
    )
    st.divider()

    # Team Name
    st.markdown('<p class="ah-section">Team Name</p>', unsafe_allow_html=True)
    team_name = st.text_input(
        "Team Name", key="reg_team_name", max_chars=80,
        placeholder="e.g. ByteBuilders", label_visibility="collapsed",
    )
    st.divider()

    # Team Size
    st.markdown('<p class="ah-section">How many Members are in your team?</p>',
                unsafe_allow_html=True)
    team_size = st.radio(
        "size", options=[4, 5, 6], key="reg_team_size",
        horizontal=True, label_visibility="collapsed",
    )
    st.divider()

    # Member Table
    st.markdown('<p class="ah-section">Team Members</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="ah-example">Example: &nbsp; John Doe &nbsp;·&nbsp; johndoe@georgiancollege.ca'
        ' &nbsp;·&nbsp; Georgian College &nbsp;·&nbsp; Computer Engineering Technology</p>',
        unsafe_allow_html=True,
    )
    members = _collect_members(team_size)
    st.divider()

    # Submit
    st.write("")
    if st.button("Submit Registration", type="primary", use_container_width=True):
        errors = _validate(team_name, team_size, members)
        if errors:
            for err in errors:
                st.error(err)
        else:
            active_members = [
                {"name": n, "email": e, "institution": inst, "program": prog}
                for n, e, inst, prog in members[:team_size]
            ]
            try:
                register_team(team_name.strip(), "", "", active_members, "")
                st.session_state["registration_submitted"] = True
                st.session_state["submitted_team_name"]    = team_name.strip()
                st.session_state["submitted_members"]      = active_members
                st.rerun()
            except Exception as exc:
                st.error(f"Submission failed — please try again. ({exc})")
