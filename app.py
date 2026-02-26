import os
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

_LOGO_LEFT  = os.path.join("assets", "georgian_logo.png")
_LOGO_RIGHT = os.path.join("assets", "autohack_logo.png")


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
    left_exists  = os.path.exists(_LOGO_LEFT)
    right_exists = os.path.exists(_LOGO_RIGHT)

    if left_exists or right_exists:
        if left_exists and right_exists:
            c1, c2, c3 = st.columns([1, 2, 1])
            with c1:
                st.image(_LOGO_LEFT, width=140)
            with c3:
                st.image(_LOGO_RIGHT, width=140)
        else:
            logo_path = _LOGO_LEFT if left_exists else _LOGO_RIGHT
            c1, c2 = st.columns([1, 4])
            with c1:
                st.image(logo_path, width=120)

    st.title("AutoHack 2026 — Judging Portal")
    st.subheader("Login")

    if not is_db_configured():
        st.error(
            "Database configuration missing. Create a .streamlit/secrets.toml with "
            "[database] uri and name. Login is disabled until configured."
        )
        st.stop()

    with st.form("login_form"):
        username  = st.text_input("Username")
        password  = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in")

        if submitted:
            user = authenticate_user(username.strip(), password)
            if user:
                st.session_state["user"] = dict(user)
                st.rerun()
            else:
                st.error("Invalid username or password.")
    st.stop()


if __name__ == "__main__":
    main()
