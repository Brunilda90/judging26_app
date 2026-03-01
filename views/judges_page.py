"""
views/judges_page.py

Admin: manage judge accounts.
Includes round assignment (prelims / finals) and prelim room assignment.
"""

import streamlit as st
from db import (
    get_judges_with_user,
    create_judge_account,
    update_judge_account,
    delete_judge_account,
    PRELIM_ROOMS,
)
from pymongo.errors import DuplicateKeyError

_ROUND_OPTIONS  = ["prelims", "finals"]
_ROUND_LABELS   = {"prelims": "🏁 Prelims", "finals": "🏆 Finals"}
_ROOM_OPTIONS   = ["-- No room --"] + PRELIM_ROOMS


def show():
    user = st.session_state.get("user")
    if not user or user.get("role") != "admin":
        st.error("Admin access required.")
        st.stop()

    st.header("Manage Judges")

    # Flash success from previous add submission
    add_success = st.session_state.pop("judge_add_success", None)
    if add_success:
        st.success(add_success)

    # If prior submission requested a reset, clear widget state before rendering
    if st.session_state.pop("reset_add_judge_form", False):
        for key in (
            "add_judge_name",
            "add_judge_username",
            "add_judge_password",
        ):
            st.session_state[key] = ""

    # ── Add judge form ────────────────────────────────────────────────────────
    with st.form("add_judge"):
        st.subheader("Add new judge")
        name     = st.text_input("Judge name",       key="add_judge_name")
        username = st.text_input("Judge username",   key="add_judge_username")
        password = st.text_input("Temporary password", type="password", key="add_judge_password")

        round_create = st.selectbox(
            "Round",
            _ROUND_OPTIONS,
            format_func=lambda x: _ROUND_LABELS[x],
            key="add_judge_round",
            help="Prelims judges score during the first round; Finals judges score the top-6.",
        )

        room_create = st.selectbox(
            "Assigned Prelim Room",
            _ROOM_OPTIONS,
            key="add_judge_room",
            help="Only applies to Prelims judges. Ignored for Finals judges.",
        )

        submitted = st.form_submit_button("Add judge")

        if submitted:
            if not name.strip() or not username.strip() or not password:
                st.error("Name, username, and password are required.")
            else:
                try:
                    new_room = (room_create if room_create != "-- No room --" else None) if round_create == "prelims" else None
                    create_judge_account(
                        name.strip(),
                        username.strip(),
                        password,
                        judge_round=round_create,
                        prelim_room=new_room,
                    )
                    st.session_state["reset_add_judge_form"] = True
                    st.session_state["judge_add_success"] = (
                        f"Added {_ROUND_LABELS[round_create]} judge account for: {name}"
                    )
                    st.rerun()
                except DuplicateKeyError:
                    st.error("Username already exists.")

    # ── Current judges list ───────────────────────────────────────────────────
    st.subheader("Current judges")

    judges = get_judges_with_user()
    if not judges:
        st.info("No judges yet.")
        return

    for judge in judges:
        j_round = judge.get("judge_round", "prelims")
        j_room  = judge.get("prelim_room")

        round_label = _ROUND_LABELS.get(j_round, j_round.capitalize())
        room_label  = f" · Room {j_room}" if j_room else ""
        expander_title = f"{judge['name']} — {round_label}{room_label}"

        with st.expander(expander_title):
            # ── Edit form ─────────────────────────────────────────────────
            with st.form(f"edit_judge_{judge['id']}"):
                name_val     = st.text_input("Name",     value=judge["name"])
                username_val = st.text_input("Username", value=judge["username"] or "")
                password_val = st.text_input(
                    "New password (leave blank to keep)", type="password"
                )

                # Round selector
                curr_round = j_round if j_round in _ROUND_OPTIONS else "prelims"
                round_val = st.selectbox(
                    "Round",
                    _ROUND_OPTIONS,
                    index=_ROUND_OPTIONS.index(curr_round),
                    format_func=lambda x: _ROUND_LABELS[x],
                    key=f"round_{judge['id']}",
                    help="Change to 'Finals' to give this judge access to the finals scoring page instead.",
                )

                # Room selector — only shown for prelims judges
                # (Finals scoring takes place in one hall; no room assignment needed)
                if j_round == "prelims":
                    curr_room = j_room if j_room in PRELIM_ROOMS else "-- No room --"
                    room_val = st.selectbox(
                        "Assigned Prelim Room",
                        _ROOM_OPTIONS,
                        index=_ROOM_OPTIONS.index(curr_room),
                        key=f"room_{judge['id']}",
                        help="Judge will only see teams that booked this room in prelims slot booking.",
                    )
                else:
                    room_val = "-- No room --"
                    st.info(
                        "ℹ️ Finals judges are not assigned to a specific room — "
                        "finals scoring takes place in one hall."
                    )

                updated = st.form_submit_button("Save changes")
                if updated:
                    if not name_val.strip() or not username_val.strip():
                        st.error("Name and username are required.")
                    else:
                        try:
                            new_room = room_val if room_val != "-- No room --" else None
                            update_judge_account(
                                judge["id"],
                                name_val.strip(),
                                username_val.strip(),
                                password=password_val or None,
                                judge_round=round_val,
                                update_room=True,
                                prelim_room=new_room,
                            )
                            st.success("Judge updated.")
                            st.rerun()
                        except DuplicateKeyError:
                            st.error("Username already exists.")

            # ── Delete form ───────────────────────────────────────────────
            with st.form(f"delete_judge_{judge['id']}"):
                st.write("Delete this judge account and all their scores?")
                delete_pressed = st.form_submit_button("Delete judge")
                if delete_pressed:
                    delete_judge_account(judge["id"])
                    st.success("Judge deleted.")
                    st.rerun()
