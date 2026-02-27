"""
views/scoring_overview_page.py

Admin: scoring overview.

Tab 1 — Judge Assignments:
  Table showing every judge's name, round, and assigned prelim room.

Tab 2 — Prelims Scores:
  Matrix table: rows = teams, columns = questions + overall avg + judge count.
  Values are the average across all judges who scored that team.

Tab 3 — Finals Scores:
  Same matrix for the finals round.
"""

import pandas as pd
import streamlit as st

from db import (
    get_judges_with_user,
    get_prelim_scoring_matrix,
    get_finals_scoring_matrix,
)

_ROUND_LABELS = {"prelims": "🏁 Prelims", "finals": "🏆 Finals"}


def _judge_assignments_tab():
    judges = get_judges_with_user()
    if not judges:
        st.info("No judges added yet.")
        return

    rows = []
    for j in judges:
        j_round = j.get("judge_round", "prelims")
        j_room  = j.get("prelim_room") or "—"
        rows.append({
            "Judge Name":   j.get("name", "—"),
            "Username":     j.get("username") or "—",
            "Round":        _ROUND_LABELS.get(j_round, j_round.capitalize()),
            "Prelim Room":  j_room if j_round == "prelims" else "N/A",
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    prelims_judges = [j for j in judges if j.get("judge_round", "prelims") == "prelims"]
    finals_judges  = [j for j in judges if j.get("judge_round") == "finals"]
    unassigned     = [j for j in prelims_judges if not j.get("prelim_room")]

    c1, c2, c3 = st.columns(3)
    c1.metric("Prelims Judges",  len(prelims_judges))
    c2.metric("Finals Judges",   len(finals_judges))
    c3.metric("No Room Assigned (Prelims)", len(unassigned))

    if unassigned:
        names = ", ".join(j["name"] for j in unassigned)
        st.warning(
            f"⚠️ The following prelims judges have no room assigned: **{names}**. "
            "Go to **Manage Judges** to assign their rooms."
        )


def _score_matrix_tab(label: str, is_finals: bool):
    fn = get_finals_scoring_matrix if is_finals else get_prelim_scoring_matrix
    questions, competitors, matrix, judge_counts = fn()

    if not competitors:
        st.info(
            f"No {label.lower()} scores have been entered yet. "
            "Scores will appear here once judges start submitting."
        )
        return

    if not questions:
        st.info("No scoring questions configured yet.")
        return

    # Truncate question prompts for column headers
    def _col_header(q):
        prompt = q.get("prompt", "")
        return prompt[:28] + "…" if len(prompt) > 28 else prompt

    q_headers = [_col_header(q) for q in questions]

    rows = []
    for c in competitors:
        cid  = c["id"]
        crow = {"Team": c["name"]}
        vals = []
        for q, hdr in zip(questions, q_headers):
            raw = matrix.get(cid, {}).get(q["id"])
            if raw is not None:
                display = f"{raw / 10:.1f}"   # convert 0-100 → 0-10 display
                vals.append(raw / 10)
            else:
                display = "—"
            crow[hdr] = display
        crow["Overall Avg"] = f"{sum(vals)/len(vals):.1f}" if vals else "—"
        crow["Judges"]      = judge_counts.get(cid, 0)
        rows.append(crow)

    # Sort by overall avg descending (treat "—" as 0)
    def _sort_key(r):
        try:
            return float(r["Overall Avg"])
        except (ValueError, TypeError):
            return 0.0

    rows.sort(key=_sort_key, reverse=True)

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    total_scored = len(competitors)
    st.caption(
        f"{total_scored} team{'s' if total_scored != 1 else ''} scored · "
        f"Scores shown as averages across all judges on a 0–10 scale."
    )


def show():
    user = st.session_state.get("user")
    if not user or user.get("role") != "admin":
        st.error("Admin access required.")
        st.stop()

    st.header("Scoring Overview")

    tab_assign, tab_prelims, tab_finals = st.tabs(
        ["👥 Judge Assignments", "🏁 Prelims Scores", "🏆 Finals Scores"]
    )

    with tab_assign:
        st.subheader("Judge Assignments")
        st.caption("Shows every judge's round and, for prelims judges, their assigned room.")
        _judge_assignments_tab()

    with tab_prelims:
        st.subheader("Prelims Scoring Matrix")
        st.caption(
            "Average scores per team per question, combined across all prelims judges. "
            "Sorted by overall average (highest first)."
        )
        _score_matrix_tab("Prelims", is_finals=False)

    with tab_finals:
        st.subheader("Finals Scoring Matrix")
        st.caption(
            "Average scores per finalist team per question, combined across all finals judges."
        )
        _score_matrix_tab("Finals", is_finals=True)
