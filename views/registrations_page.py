import streamlit as st
from db import get_team_registrations, update_registration

_KNOWN_APP_URL    = "https://judgingapp26.streamlit.app"
_MAX_MEMBERS      = 6   # public registration cap (students see 6 slots)
_ADMIN_MAX_MEMBERS = 7  # admin-only: allows adding a 7th member via edit form


def _registration_link() -> str:
    return f"{_KNOWN_APP_URL}/?page=register"


def show():
    user = st.session_state.get("user")
    if not user or user.get("role") != "admin":
        st.error("Admin access required.")
        st.stop()

    st.header("Team Registrations")

    # ── Public link ─────────────────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown("**Public Registration Link**")
        st.code(_registration_link(), language=None)
        st.caption("Share this link with teams. No login required to register.")

    st.write("")

    registrations = get_team_registrations()
    if not registrations:
        st.info("No registrations yet.")
        return

    st.caption(f"{len(registrations)} team(s) registered")
    st.divider()

    # ── Track which team is being viewed / edited ────────────────────────────────
    if "editing_reg_id" not in st.session_state:
        st.session_state["editing_reg_id"] = None
    if "viewing_reg_id" not in st.session_state:
        st.session_state["viewing_reg_id"] = None

    # ── Table header ─────────────────────────────────────────────────────────────
    hcols = st.columns([2.2, 0.7, 2.2, 1.5, 1.0, 0.9])
    hcols[0].markdown("**Team Name**")
    hcols[1].markdown("**Members**")
    hcols[2].markdown("**Member 1 Email**")
    hcols[3].markdown("**Submitted**")
    hcols[4].markdown("")
    hcols[5].markdown("")
    st.divider()

    # ── One row per team ─────────────────────────────────────────────────────────
    for reg in registrations:
        reg_id  = reg["id"]
        members = reg.get("members") or []
        created = reg.get("created_at")
        date_str = (
            created.strftime("%Y-%m-%d %H:%M")
            if hasattr(created, "strftime") else str(created or "—")
        )
        member1_email = members[0].get("email", "—") if members else "—"
        is_editing = st.session_state["editing_reg_id"] == reg_id
        is_viewing = st.session_state["viewing_reg_id"] == reg_id

        row = st.columns([2.2, 0.7, 2.2, 1.5, 1.0, 0.9])
        row[0].write(reg.get("team_name", "—"))
        row[1].write(str(len(members)))
        row[2].write(member1_email)
        row[3].write(date_str)

        # View button
        if is_viewing:
            if row[4].button("Close", key=f"close_{reg_id}"):
                st.session_state["viewing_reg_id"] = None
                st.rerun()
        else:
            if row[4].button("👁 View", key=f"view_{reg_id}"):
                st.session_state["viewing_reg_id"] = reg_id
                st.session_state["editing_reg_id"] = None
                st.rerun()

        # Edit button
        if is_editing:
            if row[5].button("Cancel", key=f"cancel_{reg_id}"):
                st.session_state["editing_reg_id"] = None
                st.rerun()
        else:
            if row[5].button("✏️ Edit", key=f"edit_{reg_id}"):
                st.session_state["editing_reg_id"] = reg_id
                st.session_state["viewing_reg_id"] = None
                st.rerun()

        # ── Inline view panel ────────────────────────────────────────────────────
        if is_viewing:
            with st.container(border=True):
                st.markdown(f"##### 👁 {reg.get('team_name', '')}")
                v1, v2 = st.columns(2)
                v1.markdown(f"**Project:** {reg.get('project_name') or '—'}")
                v2.markdown(f"**Submitted:** {date_str}")
                if reg.get("description"):
                    st.markdown(f"**Description:** {reg['description']}")
                st.markdown("**Team Members**")
                mh = st.columns([2, 2.5, 2, 2.5])
                for col, lbl in zip(mh, ["Full Name", "Email", "Institution", "Program"]):
                    col.markdown(f"<small><b>{lbl}</b></small>", unsafe_allow_html=True)
                for m in members:
                    mc = st.columns([2, 2.5, 2, 2.5])
                    mc[0].write(m.get("name", "—"))
                    mc[1].write(m.get("email", "—"))
                    mc[2].write(m.get("institution", "—"))
                    mc[3].write(m.get("program", "—"))

        # ── Inline edit form (only for the selected team) ────────────────────────
        if is_editing:
            with st.container(border=True):
                st.markdown(f"##### Editing: {reg.get('team_name', '')}")

                with st.form(key=f"form_{reg_id}"):
                    new_team_name = st.text_input(
                        "Team Name",
                        value=reg.get("team_name", ""),
                    )

                    st.markdown("**Members**")
                    mh = st.columns([2, 2.5, 2, 2.5])
                    for col, lbl in zip(mh, ["Full Name", "Email", "Institution", "Program"]):
                        col.markdown(f"<small><b>{lbl}</b></small>", unsafe_allow_html=True)

                    new_members = []
                    for i in range(1, _ADMIN_MAX_MEMBERS + 1):
                        orig = members[i - 1] if i <= len(members) else {}
                        # Visually separate the 7th member row so the admin
                        # knows it is an exceptional override slot
                        if i == 7:
                            st.markdown(
                                '<p style="font-size:0.78rem;color:#888;'
                                'font-style:italic;margin:10px 0 4px;">'
                                '⚠️ Member 7 — admin override (exception only)</p>',
                                unsafe_allow_html=True,
                            )
                        mc = st.columns([2, 2.5, 2, 2.5])
                        name  = mc[0].text_input("Name",  value=orig.get("name", ""),        key=f"n_{reg_id}_{i}", label_visibility="collapsed", placeholder=f"Member {i} name")
                        email = mc[1].text_input("Email", value=orig.get("email", ""),       key=f"e_{reg_id}_{i}", label_visibility="collapsed", placeholder="email@example.com")
                        inst  = mc[2].text_input("Inst",  value=orig.get("institution", ""), key=f"i_{reg_id}_{i}", label_visibility="collapsed", placeholder="Institution")
                        prog  = mc[3].text_input("Prog",  value=orig.get("program", ""),     key=f"p_{reg_id}_{i}", label_visibility="collapsed", placeholder="Program")
                        new_members.append((name.strip(), email.strip(), inst.strip(), prog.strip()))

                    save_col, _ = st.columns([1, 4])
                    saved = save_col.form_submit_button("💾 Save", type="primary")

                if saved:
                    updated_members = [
                        {"name": n, "email": e, "institution": ins, "program": p}
                        for n, e, ins, p in new_members
                        if n
                    ]
                    update_registration(
                        reg_id,
                        team_name=new_team_name,
                        members=updated_members,
                    )
                    st.session_state["editing_reg_id"] = None
                    st.success(f"✅ Saved changes for **{new_team_name}**.")
                    st.rerun()

        st.divider()
