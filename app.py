import os
import base64
import streamlit as st
from db import init_db, authenticate_user, get_background_color, is_db_configured
import views.judges_page as judges_page
import views.competitors_page as competitors_page
import views.scoring_page as scoring_page
import views.leaderboard_page as leaderboard_page
import views.questions_page as questions_page
import views.registrations_page as registrations_page
import views.registration_page as registration_page
import views.booking_page as booking_page
import views.admin_bookings_page as admin_bookings_page
import views.home_page as home_page
import views.scheduling_page as scheduling_page
import views.admin_scheduling_page as admin_scheduling_page
import views.mentor_schedule_page as mentor_schedule_page
import views.finals_scoring_page as finals_scoring_page
import views.scoring_overview_page as scoring_overview_page

_LOGO_LEFT    = os.path.join("assets", "georgian_logo.png")
_LOGO_RIGHT   = os.path.join("assets", "autohack_logo.png")
_LOGO_AH_SVG  = os.path.join("assets", "autohack_logo.svg")
_LOGO_AH_WHITE= os.path.join("assets", "autohack_logo_white.png")

_BG_URL = (
    "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7"
    "?auto=format&fit=crop&w=1920&q=80"
)

_LOGIN_CSS = f"""
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
    max-width: 900px !important;
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
    color: #FFFFFF; font-size: 1.10rem; font-weight: 700;
    text-align: center; margin: 0 0 6px; letter-spacing: 0.5px;
}}
.login-sub {{
    color: rgba(180,200,235,0.55); font-size: 0.82rem;
    text-align: center; margin: 0 0 24px; letter-spacing: 0.3px;
}}
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
.stMarkdown p {{ color: rgba(225,230,245,0.90) !important; }}
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


def main():
    st.set_page_config(page_title="AutoHack 2026", layout="wide")

    # Create DB indexes and seed default admin
    init_db()
    apply_background_theme()

    # --- Public routes (no login required) ---
    page_param = st.query_params.get("page", "")
    if page_param == "" or page_param == "home":
        if not st.session_state.get("user"):
            home_page.show()
            return
    if page_param == "register":
        registration_page.show()
        return
    if page_param == "book":
        booking_page.show()
        return
    if page_param == "schedule":
        scheduling_page.show()
        return
    if page_param == "mentor_schedule":
        mentor_schedule_page.show()
        return

    # --- Authenticated routes ---
    user = st.session_state.get("user")
    if not user:
        render_login()
        return

    # Sidebar: logos + title + logout
    _render_sidebar_header()
    st.sidebar.write(f"Logged in as **{user['username']}** ({user['role']})")
    if st.sidebar.button("Log out"):
        st.session_state.pop("user", None)
        st.rerun()

    if user["role"] == "admin":
        # Admin gets full navigation
        # Note: Manage Competitors and Customize pages are kept in the codebase
        # but removed from navigation (use ?page=... directly if needed)
        page = st.sidebar.radio("Navigation", [
            "Team Registrations",
            "Prelim Bookings",
            "Scheduling",
            "Manage Judges",
            "Manage Questions",
            "Scoring Overview",
            "Leaderboard",
        ])
    else:
        # Judges: no navigation radio — page is determined by their assigned round.
        # The sign-out control is embedded inside each scoring page's header.
        judge_round = user.get("judge_round", "prelims")
        page = "Finals Scoring" if judge_round == "finals" else "Prelims Scoring"

    # --- Route handlers ---
    if page == "Team Registrations":
        registrations_page.show()
    elif page == "Prelim Bookings":
        admin_bookings_page.show()
    elif page == "Scheduling":
        admin_scheduling_page.show()
    elif page == "Manage Judges":
        judges_page.show()
    elif page == "Manage Questions":
        questions_page.show()
    elif page == "Scoring Overview":
        scoring_overview_page.show()
    elif page == "Leaderboard":
        leaderboard_page.show()
    elif page == "Prelims Scoring":
        scoring_page.show()
    elif page == "Finals Scoring":
        finals_scoring_page.show()


def _render_sidebar_header():
    left_exists  = os.path.exists(_LOGO_LEFT)
    right_exists = os.path.exists(_LOGO_RIGHT)

    if left_exists and right_exists:
        c1, c2 = st.sidebar.columns(2)
        c1.image(_LOGO_LEFT,  use_container_width=True)
        c2.image(_LOGO_RIGHT, use_container_width=True)
    elif left_exists:
        st.sidebar.image(_LOGO_LEFT,  use_container_width=True)
    elif right_exists:
        st.sidebar.image(_LOGO_RIGHT, use_container_width=True)

    st.sidebar.title("AutoHack 2026")


def apply_background_theme():
    color = get_background_color()
    if not color:
        return
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-color: {color};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_login():
    # ── Determine portal context from query param ────────────────────────────────
    role = st.query_params.get("role", "")
    if role == "judge":
        portal_icon  = "⚖️"
        portal_label = "Judge Portal"
    elif role == "admin":
        portal_icon  = "⚙️"
        portal_label = "Admin Portal"
    else:
        portal_icon  = "🔐"
        portal_label = "Staff Portal"

    st.markdown(_LOGIN_CSS, unsafe_allow_html=True)

    # ── Banner ──────────────────────────────────────────────────────────────────
    ah_tag = (
        _b64_tag(_LOGO_AH_WHITE,
                 "width:100%;max-width:560px;height:auto;object-fit:contain;",
                 "AutoHack 2026")
        or _b64_tag(_LOGO_AH_SVG,
                    "width:100%;max-width:560px;height:auto;object-fit:contain;",
                    "AutoHack 2026")
        or _b64_tag(_LOGO_RIGHT,
                    "width:100%;max-width:560px;height:auto;object-fit:contain;",
                    "AutoHack 2026")
    )
    gc_tag = _b64_tag(
        _LOGO_LEFT,
        "height:44px;object-fit:contain;opacity:0.80;",
        "Georgian College"
    )
    banner = (
        '<div style="'
        '  position:relative;background:rgba(8,10,20,0.70);'
        '  border-radius:16px;padding:28px 24px 20px;'
        '  margin-bottom:4px;text-align:center;'
        '  border:1px solid rgba(255,255,255,0.07);">'
        f'  {ah_tag}'
        + (
            '<div style="position:absolute;bottom:14px;right:18px;">'
            f'{gc_tag}</div>'
            if gc_tag else ""
        )
        + '</div>'
    )
    subtitle = (
        '<div style="text-align:center;padding-top:12px;">'
        f'  <p class="ah-subtitle">{portal_label}</p>'
        '  <div class="ah-stripe"></div>'
        '</div>'
    )
    st.markdown(banner + subtitle, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # ── DB check ────────────────────────────────────────────────────────────────
    if not is_db_configured():
        st.error(
            "Database configuration missing. Create a .streamlit/secrets.toml with "
            "[database] uri and name. Login is disabled until configured."
        )
        st.stop()

    # ── Login card ──────────────────────────────────────────────────────────────
    _, col, _ = st.columns([1, 2, 1])
    with col:
        # st.markdown(
        #     f'<div class="login-card">'
        #     f'  <p class="login-title">{portal_icon} {portal_label}</p>'
        #     f'</div>',
        #     unsafe_allow_html=True,
        # )

        with st.form("login_form"):
            username  = st.text_input("Username")
            password  = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign In", type="primary",
                                              use_container_width=True)
            if submitted:
                user = authenticate_user(username.strip(), password)
                if user:
                    st.session_state["user"] = dict(user)
                    st.rerun()
                else:
                    st.error("Invalid username or password.")

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


if __name__ == "__main__":
    main()
