import streamlit as st
from db import init_db
import views.judges_page as judges_page
import views.competitors_page as competitors_page
import views.scoring_page as scoring_page
import views.leaderboard_page as leaderboard_page

def main():
    # Setup Streamlit page
    st.set_page_config(page_title="Judging Tool", layout="wide")

    # Create DB tables if needed
    init_db()

    # Sidebar navigation
    st.sidebar.title("Judging Tool")
    page = st.sidebar.radio("Navigation", [
        "Manage Judges", "Manage Competitors", "Enter Scores", "Leaderboard"
    ])

    # Route to correct page
    if page == "Manage Judges":
        judges_page.show()
    elif page == "Manage Competitors":
        competitors_page.show()
    elif page == "Enter Scores":
        scoring_page.show()
    elif page == "Leaderboard":
        leaderboard_page.show()

if __name__ == "__main__":
    main()
