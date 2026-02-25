"""
views/admin_bookings_page.py

Admin page: view and manage all prelim booking slots.
Shows a 9-slot × 3-room grid with edit/delete controls.
"""

import streamlit as st

from db import (
    PRELIM_ROOMS,
    PRELIM_SLOTS,
    get_all_bookings,
    get_booked_slot_map,
    admin_update_booking,
    admin_delete_booking,
    get_approved_team_names,
)

_KNOWN_APP_URL = "https://judgingapp26.streamlit.app"


def _booking_link() -> str:
    return f"{_KNOWN_APP_URL}/?page=book"


def show():
    user = st.session_state.get("user")
    if not user or user.get("role") != "admin":
        st.error("Admin access required.")
        st.stop()

    st.header("📋 Prelim Bookings")

    # ── Public booking link ──────────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown("**Public Booking Link** (share with registered teams)")
        st.code(_booking_link(), language=None)
        st.caption("Teams can book or switch their prelims slot at this link. No login required.")

    st.write("")

    # ── Load data ────────────────────────────────────────────────────────────────
    all_bookings = get_all_bookings()
    booked_map: dict = {}   # (slot_label, room) → booking doc
    for b in all_bookings:
        booked_map[(b["slot_label"], b["room"])] = b

    total_slots  = len(PRELIM_SLOTS) * len(PRELIM_ROOMS)
    booked_count = len(all_bookings)

    # ── Summary metrics ──────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Slots",   total_slots)
    c2.metric("Booked",        booked_count)
    c3.metric("Available",     total_slots - booked_count)

    st.divider()

    # ── Booking grid ─────────────────────────────────────────────────────────────
    st.subheader("Slot Overview")

    # Column headers
    header_cols = st.columns([2.2] + [1.6] * len(PRELIM_ROOMS))
    header_cols[0].markdown(
        "**Time Slot**",
    )
    for i, room in enumerate(PRELIM_ROOMS, start=1):
        header_cols[i].markdown(f"**Room {room}**")

    st.write("")

    for slot in PRELIM_SLOTS:
        row_cols = st.columns([2.2] + [1.6] * len(PRELIM_ROOMS))
        row_cols[0].write(slot)

        for i, room in enumerate(PRELIM_ROOMS, start=1):
            booking = booked_map.get((slot, room))
            if booking:
                row_cols[i].markdown(
                    f"🔴 **{booking['team_name']}**",
                )
            else:
                row_cols[i].markdown(
                    "<span style='color:rgba(120,240,140,0.80);'>✅ Free</span>",
                    unsafe_allow_html=True,
                )

    st.divider()

    # ── Full booking list with edit/delete ───────────────────────────────────────
    st.subheader("Manage Bookings")

    if not all_bookings:
        st.info("No bookings have been made yet.")
    else:
        approved_teams = get_approved_team_names()

        for booking in all_bookings:
            bid  = booking["id"]
            with st.expander(
                f"**{booking['team_name']}** — {booking['slot_label']}  ·  Room {booking['room']}",
                expanded=False,
            ):
                col_edit, col_del = st.columns([3, 1])

                with col_edit:
                    st.markdown("**Edit booking**")

                    new_slot = st.selectbox(
                        "New Time Slot",
                        options=PRELIM_SLOTS,
                        index=PRELIM_SLOTS.index(booking["slot_label"])
                              if booking["slot_label"] in PRELIM_SLOTS else 0,
                        key=f"edit_slot_{bid}",
                    )
                    new_room = st.selectbox(
                        "New Room",
                        options=PRELIM_ROOMS,
                        index=PRELIM_ROOMS.index(booking["room"])
                              if booking["room"] in PRELIM_ROOMS else 0,
                        key=f"edit_room_{bid}",
                    )

                    if st.button("Save Changes", key=f"save_{bid}", type="primary"):
                        try:
                            admin_update_booking(bid, new_slot, new_room)
                            st.success(
                                f"✅ Updated: **{booking['team_name']}** → "
                                f"**{new_slot}** — Room **{new_room}**"
                            )
                            st.rerun()
                        except ValueError as exc:
                            st.error(str(exc))

                with col_del:
                    st.markdown("**Remove**")
                    if st.button("🗑️ Delete", key=f"del_{bid}"):
                        st.session_state[f"confirm_del_{bid}"] = True

                    if st.session_state.get(f"confirm_del_{bid}"):
                        st.warning(f"Are you sure you want to remove the booking for **{booking['team_name']}**?")
                        yes_col, no_col = st.columns(2)
                        if yes_col.button("Yes, delete", key=f"yes_del_{bid}", type="primary"):
                            admin_delete_booking(bid)
                            st.session_state.pop(f"confirm_del_{bid}", None)
                            st.success(f"Booking for **{booking['team_name']}** removed.")
                            st.rerun()
                        if no_col.button("Cancel", key=f"no_del_{bid}"):
                            st.session_state.pop(f"confirm_del_{bid}", None)
                            st.rerun()

    st.divider()

    # ── Export ───────────────────────────────────────────────────────────────────
    if all_bookings:
        import csv, io
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=["team_name", "slot_label", "room", "booked_at"],
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(all_bookings)
        st.download_button(
            label="📥 Export Bookings CSV",
            data=output.getvalue(),
            file_name="prelim_bookings.csv",
            mime="text/csv",
        )
