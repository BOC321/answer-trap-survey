# In app.py

import streamlit as st
import os
import plotly.graph_objects as go
from database import (
    initialize_database, save_setting, load_setting,
    add_category, get_all_categories, delete_category,
    add_question, get_questions_for_category, delete_question,
    add_score_range, get_ranges_for_category, delete_score_range,
    update_score_range, get_question_details, update_question,
    load_full_survey
)
from auth import login_form
from email_utils import format_report_as_html, send_report_email

# --- Page Configuration ---
st.set_page_config(page_title="Answer Trap", layout="centered")

# --- Initialize Database ---
initialize_database()

# --- Constants ---
UPLOADS_DIR = "uploads"
if not os.path.exists(UPLOADS_DIR):
    os.makedirs(UPLOADS_DIR)

# --- Session State Initialization ---
states_to_initialize = {
    'logged_in': False, 'editing_range_id': None, 'editing_question_id': None,
    'survey_started': False, 'current_question_index': 0, 'scores': {}
}
for key, value in states_to_initialize.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ==============================================================================
# --- USER SURVEY SECTION ---
# ==============================================================================
def generate_report():
    """Generates and displays the final report, and handles emailing."""
    st.success("You have completed the survey!")
    st.balloons()
    st.header("Your Risk Profile Report")
    st.markdown("---")

    # --- Calculations ---
    final_scores = st.session_state.scores
    total_score = sum(final_scores.values())
    all_categories = get_all_categories(include_total_score=False)
    full_category_map = {cat_id: name for cat_id, name in get_all_categories(include_total_score=True)}
    total_score_cat_id = next((cat_id for cat_id, name in full_category_map.items() if name == "Total Score"), None)

    # --- Display Category Results (IN ORDER) ---
    st.subheader("Category Breakdown")
    for cat_id, cat_name in all_categories:
        score = final_scores.get(cat_id, 0)
        ranges = get_ranges_for_category(cat_id)
        report_text = "No report text defined for this score."
        display_color = "#f0f2f6"
        for r_id, r_start, r_end, r_text, r_color in ranges:
            if r_start <= score <= r_end:
                report_text = r_text
                display_color = r_color
                break
        st.markdown(f"<div style='border-left: 5px solid {display_color}; padding-left: 15px; margin-bottom: 20px; border-radius: 5px; background-color: #fafafa; padding: 15px;'>"
                    f"<h4>{cat_name}</h4>"
                    f"<h6>Your Score: {score}</h6>"
                    f"<p>{report_text}</p>"
                    "</div>", unsafe_allow_html=True)

    # --- Display Total Score Result ---
    st.markdown("---")
    st.subheader("Overall Profile")
    if total_score_cat_id:
        total_ranges = get_ranges_for_category(total_score_cat_id)
        total_report_text = "No overall report text defined for this score."
        for r_id, r_start, r_end, r_text, r_color in total_ranges:
            if r_start <= total_score <= r_end:
                total_report_text = r_text
                break
        st.write(total_report_text)

    # --- Display Graph (IN ORDER) ---
    st.markdown("---")
    st.subheader("Visual Score Summary")
    graph_labels = [cat_name for cat_id, cat_name in all_categories]
    graph_scores = [final_scores.get(cat_id, 0) for cat_id, cat_name in all_categories]
    fig = go.Figure(data=[go.Bar(x=graph_labels, y=graph_scores, marker_color='royalblue')])
    fig.update_layout(title_text='Your Scores by Category', xaxis_title="Category", yaxis_title="Score")
    st.plotly_chart(fig, use_container_width=True)

    # --- Functional Email Report Section ---
    st.markdown("---")
    st.subheader("Get a Copy of Your Report")
    survey_title = load_setting('survey_title') or "Survey Report"
    with st.form("email_form"):
        user_email = st.text_input("Enter your email address to receive a copy:")
        submitted = st.form_submit_button("Email My Report")
        if submitted:
            if user_email:
                with st.spinner("Sending your report..."):
                    html_report = format_report_as_html(
                        survey_title, final_scores, full_category_map, total_score, 
                        total_score_cat_id, get_ranges_for_category
                    )
                    success = send_report_email(
                        subject=f"Your '{survey_title}' Report",
                        html_content=html_report,
                        user_email=user_email
                    )
                    if success:
                        st.success(f"Your report has been sent to {user_email}.")
                        st.info("Please check your spam or junk folder if you do not see the email in your inbox within a few minutes.")
            else:
                st.error("Please enter a valid email address.")

    if st.button("Take Survey Again"):
        st.session_state.survey_started = False
        st.session_state.current_question_index = 0
        st.session_state.scores = {}
        st.rerun()

def user_survey_page():
    survey_title = load_setting('survey_title') or "Welcome to the Survey"
    banner_path = load_setting('banner_path')
    st.title(survey_title)
    if banner_path and os.path.exists(banner_path):
        st.image(banner_path, width=400) 
    st.markdown("---")
    survey_questions = load_full_survey()
    if not survey_questions:
        st.warning("This survey has not been configured yet. Please contact the administrator.")
        return
    if not st.session_state.survey_started:
        st.session_state.scores = {}
        st.session_state.survey_started = True
    if st.session_state.current_question_index >= len(survey_questions):
        generate_report()
        return
    current_question = survey_questions[st.session_state.current_question_index]
    (q_id, cat_id, q_text, a1_text, a1_score, a2_text, a2_score, a3_text, a3_score, cat_name) = current_question
    st.subheader(f"Category: {cat_name}")
    st.markdown(f"### {q_text}")
    def handle_answer(score, category_id):
        st.session_state.scores[category_id] = st.session_state.scores.get(category_id, 0) + score
        st.session_state.current_question_index += 1
        st.rerun()
    if st.button(a1_text, use_container_width=True):
        handle_answer(a1_score, cat_id)
    if st.button(a2_text, use_container_width=True):
        handle_answer(a2_score, cat_id)
    if st.button(a3_text, use_container_width=True):
        handle_answer(a3_score, cat_id)
    progress = (st.session_state.current_question_index) / len(survey_questions)
    st.progress(progress, text=f"Question {st.session_state.current_question_index + 1} of {len(survey_questions)}")

# ==============================================================================
# --- ADMIN PANEL SECTION ---
# ==============================================================================
def settings_page():
    st.title("Survey Settings")
    st.markdown("---")
    st.subheader("Configure the main title and banner for your survey.")
    current_title = load_setting('survey_title') or ""
    current_banner_path = load_setting('banner_path')
    with st.form("settings_form"):
        new_title = st.text_input("Survey Title", value=current_title)
        uploaded_banner = st.file_uploader("Upload Banner Image (PNG, JPG, JPEG)", type=['png', 'jpg', 'jpeg'])
        submitted = st.form_submit_button("Save Settings")
        if submitted:
            save_setting('survey_title', new_title)
            if uploaded_banner is not None:
                banner_path = os.path.join(UPLOADS_DIR, uploaded_banner.name)
                with open(banner_path, "wb") as f:
                    f.write(uploaded_banner.getbuffer())
                save_setting('banner_path', banner_path)
            st.success("Settings saved successfully!")
            st.rerun()
    if current_banner_path and os.path.exists(current_banner_path):
        st.subheader("Current Banner:")
        st.image(current_banner_path, width=300)

def categories_page():
    st.title("Survey Categories")
    st.markdown("---")
    st.subheader("Add or Remove Survey Categories")
    st.info("These are the high-level topics for your questions, e.g., 'Decision Making'.")
    with st.form("new_category_form", clear_on_submit=True):
        new_category_name = st.text_input("New Category Name")
        submitted = st.form_submit_button("Add Category")
        if submitted and new_category_name:
            add_category(new_category_name)
            st.success(f"Added category: {new_category_name}")
    st.markdown("---")
    st.subheader("Existing Categories")
    all_categories = get_all_categories()
    if not all_categories:
        st.warning("No categories created yet.")
    else:
        col1, col2 = st.columns([3, 1])
        col1.write("**Category Name**")
        col2.write("**Actions**")
        for cat_id, cat_name in all_categories:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(cat_name)
            with col2:
                if st.button("Delete", key=f"del_cat_{cat_id}"):
                    delete_category(cat_id)
                    st.rerun()

def questions_page():
    st.title("Questions & Answers")
    st.markdown("---")
    st.subheader("Add, View, and Remove Questions for each Category")
    all_categories = get_all_categories()
    if not all_categories:
        st.warning("Please add at least one category in the 'Categories' page before adding questions.")
        return
    category_dict = {name: id for id, name in all_categories}
    selected_category_name = st.selectbox("Select a Category to Manage", options=category_dict.keys())
    selected_category_id = category_dict[selected_category_name]
    st.markdown("---")
    with st.form("new_question_form", clear_on_submit=True):
        st.subheader(f"Add a New Question to '{selected_category_name}'")
        question_text = st.text_area("Question Text")
        st.write("**Answers & Scores**")
        col1, col2 = st.columns([3, 1])
        a1_text = col1.text_input("Answer 1 Text")
        a1_score = col2.number_input("Answer 1 Score", min_value=0, step=1, key="s1")
        col3, col4 = st.columns([3, 1])
        a2_text = col3.text_input("Answer 2 Text")
        a2_score = col4.number_input("Answer 2 Score", min_value=0, step=1, key="s2")
        col5, col6 = st.columns([3, 1])
        a3_text = col5.text_input("Answer 3 Text")
        a3_score = col6.number_input("Answer 3 Score", min_value=0, step=1, key="s3")
        submitted = st.form_submit_button("Add Question")
        if submitted:
            if not all([question_text, a1_text, a2_text, a3_text]):
                st.error("Please fill out the question text and all three answer texts.")
            else:
                add_question(selected_category_id, question_text, a1_text, a1_score, a2_text, a2_score, a3_text, a3_score)
                st.success(f"Added new question to '{selected_category_name}'!")
                st.rerun()
    st.markdown("---")
    st.subheader(f"Existing Questions in '{selected_category_name}'")
    questions_in_category = get_questions_for_category(selected_category_id)
    if not questions_in_category:
        st.info("No questions have been added to this category yet.")
    else:
        for q_id, q_text in questions_in_category:
            with st.expander(f"Question: {q_text[:60]}..."):
                st.write(q_text)
                b_col1, b_col2 = st.columns([1, 6])
                with b_col1:
                    if st.button("Edit", key=f"edit_q_{q_id}"):
                        st.session_state.editing_question_id = q_id
                        st.rerun()
                with b_col2:
                    if st.button("Delete", key=f"del_q_{q_id}", type="primary"):
                        delete_question(q_id)
                        st.rerun()
    if st.session_state.editing_question_id is not None:
        question_to_edit = get_question_details(st.session_state.editing_question_id)
        if question_to_edit:
            q_id, cat_id, q_text, a1_text, a1_score, a2_text, a2_score, a3_text, a3_score = question_to_edit
            @st.dialog("Edit Question")
            def edit_question_dialog():
                st.subheader("Update the details for this question:")
                new_q_text = st.text_area("Question Text", value=q_text)
                st.write("**Answers & Scores**")
                col1, col2 = st.columns([3, 1])
                new_a1_text = col1.text_input("Answer 1 Text", value=a1_text)
                new_a1_score = col2.number_input("Answer 1 Score", min_value=0, step=1, value=a1_score, key="es1")
                col3, col4 = st.columns([3, 1])
                new_a2_text = col3.text_input("Answer 2 Text", value=a2_text)
                new_a2_score = col4.number_input("Answer 2 Score", min_value=0, step=1, value=a2_score, key="es2")
                col5, col6 = st.columns([3, 1])
                new_a3_text = col5.text_input("Answer 3 Text", value=a3_text)
                new_a3_score = col6.number_input("Answer 3 Score", min_value=0, step=1, value=a3_score, key="es3")
                if st.button("Save Changes"):
                    if not all([new_q_text, new_a1_text, new_a2_text, new_a3_text]):
                        st.error("Please fill out the question text and all three answer texts.")
                    else:
                        update_question(q_id, new_q_text, new_a1_text, new_a1_score, new_a2_text, new_a2_score, new_a3_text, new_a3_score)
                        st.session_state.editing_question_id = None
                        st.rerun()
            edit_question_dialog()

def report_ranges_page():
    st.title("Report Ranges Setup")
    st.markdown("---")
    st.subheader("Define the text and colors for different score ranges.")
    st.info("This is what the user will see on their final report based on their score.")
    all_report_targets = get_all_categories(include_total_score=True)
    target_dict = {name: id for id, name in all_report_targets}
    selected_target_name = st.selectbox("Configure Report Ranges For:", options=target_dict.keys())
    selected_target_id = target_dict[selected_target_name]
    st.markdown("---")
    with st.form("new_range_form"):
        st.subheader(f"Add a New Range for '{selected_target_name}'")
        col1, col2 = st.columns(2)
        start_score = col1.number_input("Start Score", min_value=0, step=1)
        end_score = col2.number_input("End Score", min_value=0, step=1)
        display_color = st.color_picker("Display Color for this Range", "#007bff")
        report_text = st.text_area("Report Text for this Range", height=200)
        submitted = st.form_submit_button("Add Range")
        if submitted:
            if end_score <= start_score:
                st.error("End Score must be greater than Start Score.")
            else:
                add_score_range(selected_target_id, start_score, end_score, report_text, display_color)
                st.success(f"Added new range for '{selected_target_name}'.")
                st.rerun()
    st.markdown("---")
    st.subheader(f"Existing Ranges for '{selected_target_name}'")
    ranges_for_target = get_ranges_for_category(selected_target_id)
    if not ranges_for_target:
        st.info("No ranges have been defined for this target yet.")
    else:
        for r_id, r_start, r_end, r_text, r_color in ranges_for_target:
            with st.container(border=True):
                st.markdown(f"<div style='border-left: 5px solid {r_color}; padding-left: 10px;'>"
                            f"<h6>Range: {r_start} - {r_end}</h6>"
                            f"<p>{r_text}</p>"
                            "</div>", unsafe_allow_html=True)
                col1, col2 = st.columns([1, 6])
                with col1:
                    if st.button("Edit", key=f"edit_r_{r_id}"):
                        st.session_state.editing_range_id = r_id
                        st.rerun()
                with col2:
                    if st.button("Delete", key=f"del_r_{r_id}", type="primary"):
                        delete_score_range(r_id)
                        st.rerun()
    if st.session_state.editing_range_id is not None:
        range_to_edit = next((r for r in ranges_for_target if r[0] == st.session_state.editing_range_id), None)
        if range_to_edit:
            r_id, r_start, r_end, r_text, r_color = range_to_edit
            @st.dialog("Edit Range")
            def edit_range_dialog():
                st.subheader("Update the details for this range:")
                col1, col2 = st.columns(2)
                new_start = col1.number_input("Start Score", min_value=0, step=1, value=r_start)
                new_end = col2.number_input("End Score", min_value=0, step=1, value=r_end)
                new_color = st.color_picker("Display Color", value=r_color)
                new_text = st.text_area("Report Text", value=r_text, height=200)
                if st.button("Save Changes"):
                    if new_end <= new_start:
                        st.error("End Score must be greater than Start Score.")
                    else:
                        update_score_range(r_id, new_start, new_end, new_text, new_color)
                        st.session_state.editing_range_id = None
                        st.rerun()
            edit_range_dialog()

def admin_panel():
    st.set_page_config(layout="wide")
    st.sidebar.title("Navigation")
    st.sidebar.write(f"Welcome, admin!")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.set_page_config(layout="centered")
        st.rerun()

    # NOTE: The one-time import functionality has been removed from this final version.
    
    page = st.sidebar.radio("Go to", ["Dashboard", "Survey Settings", "Categories", "Questions", "Report Ranges"])
    st.sidebar.markdown("---")

    if page == "Dashboard":
        st.title("Admin Dashboard")
        st.info("Select an option from the sidebar to begin configuring your survey.")
    elif page == "Survey Settings":
        settings_page()
    elif page == "Categories":
        categories_page()
    elif page == "Questions":
        questions_page()
    elif page == "Report Ranges":
        report_ranges_page()

# ==============================================================================
# --- MAIN ROUTER ---
# ==============================================================================
query_params = st.query_params
if "mode" in query_params:
    mode = query_params["mode"]
else:
    mode = "user"

if mode == "admin":
    if not st.session_state.logged_in:
        login_form()
    else:
        admin_panel()
else:
    user_survey_page()