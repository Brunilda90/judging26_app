import streamlit as st
from db import (
    get_leaderboard,
    get_judges_with_user,
    get_competitors,
    get_questions,
    get_answers_for_judge_competitor,
    get_manual_finalists,
    set_manual_finalists,
    clear_manual_finalists,
)
import io
import csv
from datetime import datetime

def show():
    user = st.session_state.get("user")
    if not user or user.get("role") != "admin":
        st.error("Admin access required.")
        st.stop()

    st.header("Leaderboard")
    if st.button("Refresh leaderboard"):
        st.rerun()

    # Get aggregated scores
    results = get_leaderboard()
    if not results:
        st.info("No scores yet.")
        return

    # Convert result rows into dict format for Streamlit
    # Assign ranks so that tied average scores share the same rank
    data = []
    # Dense ranking: ties receive the same rank, and the next distinct score increments rank by 1
    prev_avg = None
    current_rank = 0
    for row in results:
        avg = row.get("avg_score", 0)
        if prev_avg is None:
            current_rank = 1
        elif avg != prev_avg:
            current_rank += 1
        rank = current_rank
        data.append({
            "Rank": rank,
            "Competitor": row["competitor_name"],
            "Number of Judges that entered scores": row["num_scores"],
            "Total Score": round(row["total_score"], 2),
            "Average Score": round(avg, 2),
        })
        prev_avg = avg

    st.dataframe(data)

    # CSV export: create CSV bytes and provide a download button
    if data:
        csv_buffer = io.StringIO()
        writer = csv.DictWriter(csv_buffer, fieldnames=[
            "Rank",
            "Competitor",
            "Number of Judges that entered scores",
            "Total Score",
            "Average Score",
        ])
        writer.writeheader()
        for row in data:
            writer.writerow(row)
        csv_bytes = csv_buffer.getvalue().encode("utf-8")
        filename = f"leaderboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        st.download_button(
            label="Export",
            data=csv_bytes,
            file_name=filename,
            mime="text/csv",
            help="Download current leaderboard as a CSV file",
        )

    # Detailed export: per-judge per-competitor with individual question values
    if True:
        judges = get_judges_with_user()
        competitors = get_competitors()
        questions = get_questions()
        # Build headers: judge info + competitor info + one column per question
        q_headers = [f"Q: {q['prompt']}" for q in questions]
        fieldnames = [
            "Judge ID",
            "Judge Name",
            "Username",
            "Judge Email",
            "Competitor ID",
            "Competitor",
            "Competitor Notes",
        ] + q_headers + ["Average Score"]

        detailed_buffer = io.StringIO()
        writer = csv.DictWriter(detailed_buffer, fieldnames=fieldnames)
        writer.writeheader()
        for j in judges:
            j_id = j.get("id")
            j_name = j.get("name")
            j_user = j.get("username")
            j_email = j.get("email")
            for c in competitors:
                row = {
                    "Judge ID": j_id,
                    "Judge Name": j_name,
                    "Username": j_user,
                    "Judge Email": j_email,
                    "Competitor ID": c.get("id"),
                    "Competitor": c.get("name"),
                    "Competitor Notes": c.get("notes", ""),
                }
                answers = get_answers_for_judge_competitor(j_id, c.get("id"))
                vals = []
                for q in questions:
                    raw = answers.get(q.get("id"))
                    if raw is None:
                        cell = ""
                    else:
                        try:
                            # stored as multiples of 10 — convert back to 0-10 scale
                            cell = float(raw) / 10.0
                        except Exception:
                            cell = raw
                    row[f"Q: {q['prompt']}"] = cell
                    if cell != "":
                        try:
                            vals.append(float(cell))
                        except Exception:
                            pass
                # avg of question values (0-10), empty if no vals
                row["Average Score"] = round(sum(vals) / len(vals), 2) if vals else ""
                writer.writerow(row)

        detailed_bytes = detailed_buffer.getvalue().encode("utf-8")
        detailed_name = f"detailed_submissions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        st.download_button(
            label="Export detailed submissions (CSV)",
            data=detailed_bytes,
            file_name=detailed_name,
            mime="text/csv",
            help="Download per-judge, per-competitor question-level submissions",
        )

    # ── Finals Selection ───────────────────────────────────────────────────────
    st.divider()
    st.subheader("🏆 Finals Selection")
    st.caption(
        "Choose which teams advance to the Finals round. "
        "The selected teams will appear in the Finals Judge Portal dropdown. "
        "If no selection is saved, the portal uses the automatic top-6 by prelim average score."
    )

    # All scored competitors in rank order (same as the leaderboard above)
    scored_results = [r for r in results if r.get("num_scores", 0) > 0]
    option_names   = [r["competitor_name"] for r in scored_results]
    by_name        = {r["competitor_name"]: r for r in scored_results}

    current_finalists = get_manual_finalists()
    current_names     = [f["competitor_name"] for f in current_finalists]

    if current_finalists:
        st.success(
            f"✅ **{len(current_finalists)} finalist(s) manually selected** — "
            "these are shown in the Finals Judge Portal."
        )
    else:
        auto_names = option_names[:6]
        if auto_names:
            st.info(
                f"**Auto mode** — Finals Portal will show the top {len(auto_names)} "
                f"team(s) by prelim score: {', '.join(auto_names)}"
            )
        else:
            st.warning("No scored teams yet — score prelims before selecting finalists.")

    selected_names = st.multiselect(
        "Select teams for Finals (max 6)",
        options=option_names,
        default=[n for n in current_names if n in option_names],
        max_selections=6,
        help="Only teams that have received at least one prelim score are listed.",
    )

    col_save, col_clear, _ = st.columns([2, 2, 4])
    with col_save:
        if st.button("Save Finalists", type="primary", use_container_width=True):
            if not selected_names:
                st.error("Select at least 1 team before saving.")
            else:
                finalist_dicts = [
                    {
                        "competitor_id":   by_name[n]["competitor_id"],
                        "competitor_name": by_name[n]["competitor_name"],
                        "avg_score":       by_name[n].get("avg_score", 0),
                        "num_scores":      by_name[n].get("num_scores", 0),
                    }
                    for n in selected_names
                ]
                set_manual_finalists(finalist_dicts)
                st.success(f"✅ {len(finalist_dicts)} finalist(s) saved to Finals Portal!")
                st.rerun()
    with col_clear:
        if current_finalists:
            if st.button("Clear — use auto top-6", use_container_width=True):
                clear_manual_finalists()
                st.rerun()
