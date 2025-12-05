import streamlit as st
from pathlib import Path
from datetime import datetime
from backend.scraper import SyllabusScraper
from backend.sb_functions import save_courses, save_settings

# Stop if user not logged in

if "uid" not in st.session_state or not st.session_state["uid"]:
    st.error("You must be logged in to access this page.")
    st.stop()

# Page configuration
st.set_page_config(layout="wide")
st.title("Upload Syllabus PDFs")

# Get OpenAI API key from secrets
API_KEY = (
    st.secrets.get("OPENAI_API_KEY")
    if "OPENAI_API_KEY" in st.secrets
    else None
)

# Create uploads directory if it doesn't exist
Path("uploads").mkdir(exist_ok=True)

st.subheader("Semester Settings")

# Input fields for semester dates
col1, col2 = st.columns(2)

with col1:
    semester_start = st.text_input(
        "Semester Start (YYYY-MM-DD)",
        value=st.session_state.get("settings", {}).get("semester_start", ""),
        placeholder="YYYY-MM-DD"
    )

with col2:
    semester_end = st.text_input(
        "Semester End (YYYY-MM-DD)",
        value=st.session_state.get("settings", {}).get("semester_end", ""),
        placeholder="YYYY-MM-DD"
    )


# Helper date validation
def validate_date(date_str, label):
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True, ""
    except ValueError as e:
        if "does not match format" in str(e):
            return False, f"{label} must be in YYYY-MM-DD format (e.g., 2025-09-04)"
        if "day is out of range" in str(e):
            return False, f"{label} is not a real calendar date"
        return False, f"{label} is invalid"


# Save semester dates button
if st.button("Save Semester Dates", use_container_width=True):
    valid = True

    # Empty field check
    if not semester_start:
        st.error("Please enter a semester start date")
        valid = False
    if not semester_end:
        st.error("Please enter a semester end date")
        valid = False

    # Validate dates
    if valid:
        ok, message = validate_date(semester_start, "Semester start date")
        if not ok:
            st.error(message)
            valid = False

        ok, message = validate_date(semester_end, "Semester end date")
        if not ok:
            st.error(message)
            valid = False

    # Save dates if valid
    if valid:
        st.session_state["semester_start"] = semester_start
        st.session_state["semester_end"] = semester_end

        if "settings" not in st.session_state:
            st.session_state["settings"] = {}

        st.session_state["settings"]["semester_start"] = semester_start
        st.session_state["settings"]["semester_end"] = semester_end

        if "uid" in st.session_state:
            save_settings(st.session_state["uid"], st.session_state["settings"])
            st.success("Semester dates saved!")
        else:
            st.error("Please log in to save dates")

st.divider()

# File uploader for syllabus PDFs
uploads = st.file_uploader(
    "Upload one or more syllabus PDFs",
    type=["pdf"],
    accept_multiple_files=True
)

# Parse all uploaded syllabi
if uploads and st.button("Parse All Syllabi", use_container_width=True):
    # Get saved semester dates
    saved_start = st.session_state.get("settings", {}).get("semester_start")
    saved_end = st.session_state.get("settings", {}).get("semester_end")

    error_messages = []

    # Must exist
    if not saved_start:
        error_messages.append("Semester start date is not set")
    if not saved_end:
        error_messages.append("Semester end date is not set")

    # Detect unsaved changes
    if semester_start != saved_start or semester_end != saved_end:
        error_messages.append("You changed the dates but didn't click 'Save Semester Dates'")

    # Validate saved dates
    if saved_start:
        ok, message = validate_date(saved_start, "Saved semester start date")
        if not ok:
            error_messages.append(message)

    if saved_end:
        ok, message = validate_date(saved_end, "Saved semester end date")
        if not ok:
            error_messages.append(message)

    # Show errors if any
    if error_messages:
        st.error("Cannot parse syllabi: " + ", ".join(error_messages))
        st.stop()

    # Initialize scraper
    scraper = SyllabusScraper(API_KEY)

    # Process PDFs
    parsed_courses = st.session_state.get("courses", {}).copy()
    progress = st.progress(0)

    for i, up in enumerate(uploads, start=1):
        # Save uploaded file temporarily
        tmp_path = Path("uploads") / up.name
        with tmp_path.open("wb") as f:
            f.write(up.getbuffer())

        # Parse syllabus
        with st.spinner(f"Parsing {up.name}..."):
            data = scraper.scrape_syllabus(
                pdf_path=str(tmp_path),
                semester_start=saved_start,
                semester_end=saved_end
            )

        # Use course code if detected, otherwise filename
        course_code = data.get("course_info", {}).get("course_code", up.name)
        parsed_courses[course_code] = data

        progress.progress(i / len(uploads))

    # Save parsed courses
    st.session_state["courses"] = parsed_courses

    if "uid" in st.session_state:
        save_courses(st.session_state["uid"], parsed_courses)

    st.success("All syllabi parsed and saved!")
