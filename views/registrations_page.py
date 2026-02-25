import pandas as pd
import streamlit as st
from db import get_team_registrations, update_registration

_KNOWN_APP_URL = "https://judgingapp26.streamlit.app"
_MAX_MEMBERS   = 6


def _registration_link() -> str:
    return f"{_KNOWN_APP_URL}/?page=register"


def show():
    user = st.session_state.get("user")
    if not user or user.get("role") != "admin":
        st.error("Admin access required.")
        st.stop()

    st.header("Team Registrations")

    # Registration link
    with st.container(border=True):
        st.markdown("**Public Registration Link**")
        st.code(_registration_link(), language=None)
        st.caption("Share this link with teams. No login required to register.")

    st.write("")

    registrations = get_team_registrations()
    if not registrations:
        st.info("No registrations yet.")
        return

    st.caption(f"{len(registrations)} registration(s) total")

    # ── Build flat DataFrame ────────────────────────────────────────────────────
    # One row per team.  Member 1 … Member 6 hold editable names.
    # Email / Institution / Program stay visible in the expander below.
    rows = []
    for reg in registrations:
        created  = reg.get("created_at")
        date_str = (
            created.strftime("%Y-%m-%d %H:%M")
            if hasattr(created, "strftime") else str(created)
        )
        members = reg.get("members") or []
        row = {
            "_id":       str(reg["id"]),
            "Team Name": reg.get("team_name", ""),
            "Submitted": date_str,
            "Notes":     reg.get("admin_notes", ""),
        }
        for i in range(1, _MAX_MEMBERS + 1):
            row[f"Member {i}"] = members[i - 1].get("name", "") if i <= len(members) else ""
        rows.append(row)

    df = pd.DataFrame(rows)

    # ── Column config ───────────────────────────────────────────────────────────
    col_cfg = {
        "_id":       None,   # hidden
        "Team Name": st.column_config.TextColumn("Team Name", width="medium"),
        "Submitted": st.column_config.TextColumn("Submitted", disabled=True, width="small"),
        "Notes":     st.column_config.TextColumn("Admin Notes", width="medium"),
    }
    for i in range(1, _MAX_MEMBERS + 1):
        col_cfg[f"Member {i}"] = st.column_config.TextColumn(
            f"Member {i}", width="medium"
        )

    st.subheader("All Registrations")
    st.caption("Edit any cell directly, then click **Save Changes**.")

    edited = st.data_editor(
        df,
        column_config=col_cfg,
        column_order=[
            "Team Name",
            *[f"Member {i}" for i in range(1, _MAX_MEMBERS + 1)],
            "Submitted",
            "Notes",
        ],
        use_container_width=True,
        num_rows="fixed",
        hide_index=True,
        key="registrations_editor",
    )

    if st.button("Save Changes", type="primary"):
        # Index original members by registration id so we can preserve
        # email / institution / program when only names are edited.
        orig_map = {str(reg["id"]): reg.get("members") or [] for reg in registrations}

        for _, row in edited.iterrows():
            reg_id   = row["_id"]
            orig_mem = list(orig_map.get(reg_id, []))

            updated_members = []
            for i in range(1, _MAX_MEMBERS + 1):
                new_name = str(row.get(f"Member {i}", "")).strip()
                idx = i - 1
                if idx < len(orig_mem):
                    # Slot existed — update name, keep other fields
                    m = dict(orig_mem[idx])
                    m["name"] = new_name
                    if new_name:                   # drop member if name cleared
                        updated_members.append(m)
                elif new_name:
                    # Admin added a new member row (name only)
                    updated_members.append({
                        "name": new_name, "email": "",
                        "institution": "", "program": "",
                    })

            update_registration(
                reg_id,
                team_name=row["Team Name"],
                admin_notes=row["Notes"],
                members=updated_members,
            )

        st.success(f"Saved {len(edited)} registration(s).")
        st.rerun()

    # ── Member detail expanders (email / institution / program) ────────────────
    st.divider()
    st.subheader("Full Member Details")

    for reg in registrations:
        members = reg.get("members") or []
        with st.expander(f"**{reg['team_name']}** — {len(members)} member(s)"):
            if not members:
                st.write("No member data recorded.")
                continue

            hc = st.columns([2, 2.5, 2, 2.5])
            for col, lbl in zip(hc, ["Full Name", "Email", "Institution", "Program"]):
                col.markdown(f"**{lbl}**")

            for m in members:
                mc = st.columns([2, 2.5, 2, 2.5])
                mc[0].write(m.get("name",        "—"))
                mc[1].write(m.get("email",       "—"))
                mc[2].write(m.get("institution", "—"))
                mc[3].write(m.get("program",     "—"))
