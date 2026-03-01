"""
views/admin_scheduling_page.py

Admin page: view and manage all mentor & robot scheduling bookings.
Shows a full grid overview plus per-booking edit/delete controls.
"""

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
    get_all_mentor_bookings,
    get_all_robot_bookings,
    admin_update_mentor_booking,
    admin_update_robot_booking,
    admin_delete_mentor_booking,
    admin_delete_robot_booking,
)

_KNOWN_APP_URL = "https://judgingapp26.streamlit.app"


def _schedule_link() -> str:
    return f"{_KNOWN_APP_URL}/?page=mentor-robot-schedule"


def _is_friday(slot_label: str) -> bool:
    return slot_label.startswith("Fri")


# ── Mentor Schedule tab ──────────────────────────────────────────────────────────

def _mentor_tab():
    all_bookings = get_all_mentor_bookings()

    # Build lookup: (slot_label, mentor_name) → booking doc
    booked_map: dict = {}
    for b in all_bookings:
        booked_map[(b["slot_label"], b["mentor_name"])] = b

    total_slots  = len(SCHED_ALL_SLOTS) * len(MENTOR_NAMES)
    booked_count = len(all_bookings)

    # ── Public link ──────────────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown("**Public Scheduling Link** (share with registered teams)")
        st.code(_schedule_link(), language=None)
        st.caption("Teams can book mentor and robot sessions at this link. No login required.")

    st.write("")

    # ── Metrics ──────────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Mentor Slots", total_slots)
    c2.metric("Booked",             booked_count)
    c3.metric("Available",          total_slots - booked_count)

    st.divider()

    # ── Grid overview ─────────────────────────────────────────────────────────
    st.subheader("Mentor Slot Overview")

    n = len(MENTOR_NAMES)
    col_widths = [2.2] + [1.1] * n
    hcols = st.columns(col_widths)
    hcols[0].markdown("**Time Slot**")
    for i, m in enumerate(MENTOR_NAMES, start=1):
        hcols[i].markdown(f"**{m}**")

    last_day = None
    for slot in SCHED_ALL_SLOTS:
        day = "Friday Mar 6" if _is_friday(slot) else "Saturday Mar 7"
        if day != last_day:
            last_day = day
            st.markdown(
                f"<p style='color:rgba(220,160,0,0.80);font-size:0.78rem;"
                f"font-weight:700;margin:8px 0 2px;'>&#9654; {day}</p>",
                unsafe_allow_html=True,
            )
        row = st.columns(col_widths)
        short = slot.split("\u00b7", 1)[-1].strip()
        row[0].write(short)
        for i, mentor in enumerate(MENTOR_NAMES, start=1):
            bk = booked_map.get((slot, mentor))
            if bk:
                row[i].markdown(f"\U0001f534 **{bk['team_name']}**")
            else:
                row[i].markdown(
                    "<span style='color:rgba(120,240,140,0.80);'>\u2705 Free</span>",
                    unsafe_allow_html=True,
                )

    st.divider()

    # ── Manage bookings ───────────────────────────────────────────────────────
    st.subheader("Manage Mentor Bookings")

    if not all_bookings:
        st.info("No mentor bookings have been made yet.")
        return

    for booking in all_bookings:
        bid = booking["id"]
        day_tag = "Fri" if _is_friday(booking["slot_label"]) else "Sat"
        with st.expander(
            f"**{booking['team_name']}** — {booking['mentor_name']}  ·  "
            f"{booking['slot_label'].split(chr(183), 1)[-1].strip()} ({day_tag})",
            expanded=False,
        ):
            col_edit, col_del = st.columns([3, 1])

            with col_edit:
                st.markdown("**Edit booking**")
                new_mentor = st.selectbox(
                    "Mentor",
                    options=MENTOR_NAMES,
                    index=MENTOR_NAMES.index(booking["mentor_name"])
                          if booking["mentor_name"] in MENTOR_NAMES else 0,
                    key=f"edit_m_mentor_{bid}",
                )
                new_slot = st.selectbox(
                    "Time Slot",
                    options=SCHED_ALL_SLOTS,
                    index=SCHED_ALL_SLOTS.index(booking["slot_label"])
                          if booking["slot_label"] in SCHED_ALL_SLOTS else 0,
                    key=f"edit_m_slot_{bid}",
                )
                if st.button("Save Changes", key=f"save_m_{bid}", type="primary"):
                    try:
                        admin_update_mentor_booking(bid, new_mentor, new_slot)
                        st.success(
                            f"\u2705 Updated: **{booking['team_name']}** \u2192 "
                            f"**{new_mentor}** at **{new_slot}**"
                        )
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))

            with col_del:
                st.markdown("**Remove**")
                if st.button("\U0001f5d1\ufe0f Delete", key=f"del_m_{bid}"):
                    st.session_state[f"confirm_del_m_{bid}"] = True

                if st.session_state.get(f"confirm_del_m_{bid}"):
                    st.warning(
                        f"Remove **{booking['team_name']}**'s mentor booking?"
                    )
                    y, n_btn = st.columns(2)
                    if y.button("Yes, delete", key=f"yes_del_m_{bid}", type="primary"):
                        admin_delete_mentor_booking(bid)
                        st.session_state.pop(f"confirm_del_m_{bid}", None)
                        st.success("Booking removed.")
                        st.rerun()
                    if n_btn.button("Cancel", key=f"no_del_m_{bid}"):
                        st.session_state.pop(f"confirm_del_m_{bid}", None)
                        st.rerun()

    st.divider()

    # ── Export CSV ────────────────────────────────────────────────────────────
    import csv, io
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["team_name", "room", "time", "booked_at"],
    )
    writer.writeheader()
    for b in all_bookings:
        # Derive room from MENTOR_ROOM_MAP (stored doc may not carry a room field)
        room = b.get("room") or MENTOR_ROOM_MAP.get(b.get("mentor_name", ""), b.get("mentor_name", ""))
        # Extract just the time portion from slot_label (strip "Fri · " / "Sat · " prefix)
        time_str = b.get("slot_label", "").split("\u00b7", 1)[-1].strip()
        writer.writerow({
            "team_name": b.get("team_name", ""),
            "room":      room,
            "time":      time_str,
            "booked_at": b.get("booked_at", ""),
        })
    st.download_button(
        label="\U0001f4e5 Export Mentor Bookings CSV",
        data=output.getvalue(),
        file_name="mentor_bookings.csv",
        mime="text/csv",
    )


# ── Robot Schedule tab ───────────────────────────────────────────────────────────

def _robot_tab():
    all_bookings = get_all_robot_bookings()

    booked_map: dict = {}
    for b in all_bookings:
        booked_map[(b["slot_label"], b["room"])] = b

    total_slots  = len(SCHED_ALL_SLOTS) * len(SCHED_ROBOT_ROOMS)
    booked_count = len(all_bookings)

    # ── Metrics ──────────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Robot Slots", total_slots)
    c2.metric("Booked",            booked_count)
    c3.metric("Available",         total_slots - booked_count)

    st.divider()

    # ── Grid overview ─────────────────────────────────────────────────────────
    st.subheader("Robot Slot Overview")

    col_widths = [2.2] + [1.6] * len(SCHED_ROBOT_ROOMS)
    hcols = st.columns(col_widths)
    hcols[0].markdown("**Time Slot**")
    for i, room in enumerate(SCHED_ROBOT_ROOMS, start=1):
        hcols[i].markdown(f"**Robot {room}**")

    last_day = None
    for slot in SCHED_ALL_SLOTS:
        day = "Friday Mar 6" if _is_friday(slot) else "Saturday Mar 7"
        if day != last_day:
            last_day = day
            st.markdown(
                f"<p style='color:rgba(220,160,0,0.80);font-size:0.78rem;"
                f"font-weight:700;margin:8px 0 2px;'>&#9654; {day}</p>",
                unsafe_allow_html=True,
            )
        row = st.columns(col_widths)
        short = slot.split("\u00b7", 1)[-1].strip()
        row[0].write(short)
        for i, room in enumerate(SCHED_ROBOT_ROOMS, start=1):
            bk = booked_map.get((slot, room))
            if bk:
                row[i].markdown(f"\U0001f534 **{bk['team_name']}**")
            else:
                row[i].markdown(
                    "<span style='color:rgba(120,240,140,0.80);'>\u2705 Free</span>",
                    unsafe_allow_html=True,
                )

    st.divider()

    # ── Manage bookings ───────────────────────────────────────────────────────
    st.subheader("Manage Robot Bookings")

    if not all_bookings:
        st.info("No robot bookings have been made yet.")
        return

    for booking in all_bookings:
        bid = booking["id"]
        day_tag = "Fri" if _is_friday(booking["slot_label"]) else "Sat"
        with st.expander(
            f"**{booking['team_name']}** — Robot {booking['room']}  ·  "
            f"{booking['slot_label'].split(chr(183), 1)[-1].strip()} ({day_tag})",
            expanded=False,
        ):
            col_edit, col_del = st.columns([3, 1])

            with col_edit:
                st.markdown("**Edit booking**")
                new_room = st.selectbox(
                    "Robot Room",
                    options=SCHED_ROBOT_ROOMS,
                    index=SCHED_ROBOT_ROOMS.index(booking["room"])
                          if booking["room"] in SCHED_ROBOT_ROOMS else 0,
                    key=f"edit_r_room_{bid}",
                )
                new_slot = st.selectbox(
                    "Time Slot",
                    options=SCHED_ALL_SLOTS,
                    index=SCHED_ALL_SLOTS.index(booking["slot_label"])
                          if booking["slot_label"] in SCHED_ALL_SLOTS else 0,
                    key=f"edit_r_slot_{bid}",
                )
                if st.button("Save Changes", key=f"save_r_{bid}", type="primary"):
                    try:
                        admin_update_robot_booking(bid, new_room, new_slot)
                        st.success(
                            f"\u2705 Updated: **{booking['team_name']}** \u2192 "
                            f"Robot **{new_room}** at **{new_slot}**"
                        )
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))

            with col_del:
                st.markdown("**Remove**")
                if st.button("\U0001f5d1\ufe0f Delete", key=f"del_r_{bid}"):
                    st.session_state[f"confirm_del_r_{bid}"] = True

                if st.session_state.get(f"confirm_del_r_{bid}"):
                    st.warning(
                        f"Remove **{booking['team_name']}**'s robot booking?"
                    )
                    y, n_btn = st.columns(2)
                    if y.button("Yes, delete", key=f"yes_del_r_{bid}", type="primary"):
                        admin_delete_robot_booking(bid)
                        st.session_state.pop(f"confirm_del_r_{bid}", None)
                        st.success("Booking removed.")
                        st.rerun()
                    if n_btn.button("Cancel", key=f"no_del_r_{bid}"):
                        st.session_state.pop(f"confirm_del_r_{bid}", None)
                        st.rerun()

    st.divider()

    import csv, io
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["team_name", "room", "slot_label", "booked_at"],
        extrasaction="ignore",
    )
    writer.writeheader()
    writer.writerows(all_bookings)
    st.download_button(
        label="\U0001f4e5 Export Robot Bookings CSV",
        data=output.getvalue(),
        file_name="robot_bookings.csv",
        mime="text/csv",
    )


# ── Main entry point ─────────────────────────────────────────────────────────────

def show():
    user = st.session_state.get("user")
    if not user or user.get("role") != "admin":
        st.error("Admin access required.")
        st.stop()

    st.header("\U0001f4c5 Mentor & Robot Scheduling")

    tab_mentor, tab_robot = st.tabs(
        ["\U0001f9d1\u200d\U0001f3eb Mentor Schedule", "\U0001f916 Robot Schedule"]
    )

    with tab_mentor:
        _mentor_tab()

    with tab_robot:
        _robot_tab()
