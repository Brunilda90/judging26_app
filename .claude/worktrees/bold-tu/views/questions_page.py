import streamlit as st
from db import (
    get_questions,
    insert_question,
    update_question,
    delete_question,
    get_intro_message,
    set_intro_message,
    clear_intro_message,
)


def show():
    # Admin gate
    user = st.session_state.get("user")
    if not user or user.get("role") != "admin":
        st.error("Admin access required.")
        st.stop()

    st.header("Manage Questions")

    add_success = st.session_state.pop("question_add_success", None)
    if add_success:
        st.success(add_success)

    if st.session_state.pop("reset_add_question_form", False):
        st.session_state["add_question_prompt"] = ""

    render_intro_message_editor()
    render_add_form()
    render_question_list()


def render_add_form():
    st.subheader("Add a question")
    with st.form("add_question"):
        prompt = st.text_input("Question prompt", key="add_question_prompt")
        submitted = st.form_submit_button("Add question")
        if submitted:
            if not prompt.strip():
                st.error("Prompt is required.")
            else:
                insert_question(prompt.strip())
                st.session_state["reset_add_question_form"] = True
                st.session_state["question_add_success"] = "Question added."
                st.rerun()


def render_question_list():
    st.subheader("Current questions")
    questions = get_questions()
    if not questions:
        st.info("No questions yet.")
        return

    for q in questions:
        with st.expander(f"{q['prompt']}"):
            render_edit_form(q)
            render_delete_form(q)


def render_edit_form(question):
    with st.form(f"edit_q_{question['id']}"):
        prompt_val = st.text_input("Prompt", value=question["prompt"])
        save = st.form_submit_button("Save changes")
        if save:
            if not prompt_val.strip():
                st.error("Prompt is required.")
            else:
                update_question(question["id"], prompt_val.strip())
                st.success("Question updated.")
                st.rerun()


def render_delete_form(question):
    with st.form(f"delete_q_{question['id']}"):
        st.write("Delete this question and its answers?")
        delete_pressed = st.form_submit_button("Delete question")
        if delete_pressed:
            delete_question(question["id"])
            st.success("Question deleted.")
            st.rerun()

def render_intro_message_editor():
    st.subheader("Judge intro message")
    st.caption(
        "Shown to judges above the team selector. Supports **Markdown** formatting: "
        "`**bold**`, `*italic*`, bullet lists with `-` or `*`, line breaks. "
        "Preview updates when you click outside the text box."
    )
    current = get_intro_message() or ""

    # Two-column layout: editor (left) | live preview (right)
    col_edit, col_preview = st.columns([1, 1])

    with col_edit:
        st.caption("✏️ Edit")
        new_text = st.text_area(
            "Intro message (Markdown)",
            value=current,
            height=180,
            key="intro_md_editor",
            label_visibility="collapsed",
            placeholder="e.g. Welcome judges! Please score each team on all criteria before moving to the next.",
        )

    with col_preview:
        st.caption("👁 Preview (as judges will see it)")
        preview_text = st.session_state.get("intro_md_editor", current)
        if preview_text and preview_text.strip():
            st.info(preview_text)
        else:
            st.markdown(
                '<p style="color:#999;font-style:italic;font-size:0.85rem;">'
                'No intro message — preview will appear here as you type.</p>',
                unsafe_allow_html=True,
            )

    col_save, col_clear = st.columns([1, 1])
    with col_save:
        if st.button("💾 Save intro message", key="save_intro_btn"):
            set_intro_message(new_text.strip())
            st.success("Intro message saved.")
            st.rerun()
    with col_clear:
        if st.button("🗑️ Clear intro message", key="clear_intro_btn"):
            clear_intro_message()
            st.success("Intro message cleared.")
            st.rerun()

    st.divider()
