import streamlit as st
from utils.normalize import normalize_type
from backend.sb_functions import save_settings

# Stop if user not logged in

if "uid" not in st.session_state or not st.session_state["uid"]:
    st.error("You must be logged in to access this page.")
    st.stop()

st.title("Study Settings & Preferences")

# Check if syllabi have been uploaded
if "courses" not in st.session_state or not st.session_state["courses"]:
    st.warning("No parsed syllabi found. Go to Upload page first.")
    st.stop()

courses = st.session_state["courses"]

# Collect all unique assessment types from uploaded syllabi
found_types = set()
for course_data in courses.values():
    assessments = course_data.get("assessments", {}).get("breakdown", [])
    for a in assessments:
        raw = a.get("type", "")
        found_types.add(normalize_type(raw))

found_types = sorted(found_types)

st.subheader("Semester Dates")

# Display saved semester dates
stored_settings = st.session_state.get("settings", {})
semester_start = stored_settings.get("semester_start", "Not set")
semester_end = stored_settings.get("semester_end", "Not set")

st.info(f"**Semester Start:** {semester_start}  \n**Semester End:** {semester_end}")
st.caption("To change semester dates, go to the Upload page")

st.divider()

st.subheader("Daily Study Hours")

# Default daily hours
default_daily = {
    "monday": 0, "tuesday": 0, "wednesday": 0,
    "thursday": 0, "friday": 0, "saturday": 0, "sunday": 0
}

stored_daily = st.session_state.get("settings", {}).get("daily_hours", default_daily)

days = list(default_daily.keys())
display_daily = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# Create input fields for each day of the week
daily_hours = {}
cols = st.columns(7)
for i, day in enumerate(days):
    with cols[i]:
        daily_hours[day] = st.number_input(
            display_daily[i],
            0.0, 24.0,
            float(stored_daily.get(day, 0)),
            step=0.5
        )

st.divider()

# Work-ahead days configuration
with st.expander("Work-Ahead Defaults (Days Before Due Date)", expanded=False):
    default_work_days = {
        "assignment": 7, "quiz": 3, "lab": 1,
        "midterm": 10, "exam": 20, "final": 20,
        "project": 20, "presentation": 7,
        "essay": 20, "report": 10,
        "case_study": 3, "discussion": 1,
        "reading": 1, "homework": 1,
        "participation": 0
    }

    stored_work = st.session_state.get("settings", {}).get("work_ahead_days", {})

    work_ahead_days = {}

    for t in found_types:
        display_name = t.capitalize().replace("_", " ")
        work_ahead_days[t] = st.number_input(
            f"{display_name} (days before due date)",
            0, 90,
            int(stored_work.get(t, default_work_days.get(t, 0)))
        )

st.divider()

# Base hours configuration
with st.expander("Default Base Hours per Assessment Type", expanded=False):
    default_base_hours = {
        "assignment": 4, "quiz": 3, "lab": 3,
        "midterm": 12, "exam": 20, "final": 20,
        "project": 25, "presentation": 10,
        "essay": 20, "report": 10,
        "case_study": 8, "discussion": 2,
        "reading": 2, "homework": 2,
        "participation": 1
    }

    stored_base = st.session_state.get("settings", {}).get("base_hours", {})

    base_hours = {}

    for t in found_types:
        display_name = t.capitalize().replace("_", " ")
        base_hours[t] = st.number_input(
            f"{display_name} Hours",
            1, 200,
            int(stored_base.get(t, default_base_hours.get(t, 3)))
        )

# Check if user has unsaved changes
has_changes = False

for day in days:
    if daily_hours.get(day, 0) != stored_daily.get(day, 0):
        has_changes = True
        break

if not has_changes:
    for t in found_types:
        if work_ahead_days.get(t, 0) != stored_work.get(t, default_work_days.get(t, 0)):
            has_changes = True
            break

if not has_changes:
    for t in found_types:
        if base_hours.get(t, 0) != stored_base.get(t, default_base_hours.get(t, 3)):
            has_changes = True
            break

if has_changes:
    st.warning("You have unsaved changes. Click 'Save Settings' below to apply them.")

# Save all settings
if st.button("Save Settings"):
    complete_daily = {
        "monday": daily_hours.get("monday", 0),
        "tuesday": daily_hours.get("tuesday", 0),
        "wednesday": daily_hours.get("wednesday", 0),
        "thursday": daily_hours.get("thursday", 0),
        "friday": daily_hours.get("friday", 0),
        "saturday": daily_hours.get("saturday", 0),
        "sunday": daily_hours.get("sunday", 0),
    }

    st.session_state["settings"] = {
        "semester_start": semester_start,
        "semester_end": semester_end,
        "daily_hours": complete_daily,
        "work_ahead_days": work_ahead_days,
        "base_hours": base_hours
    }

    if "uid" in st.session_state:
        save_settings(st.session_state["uid"], st.session_state["settings"])

    # Clear cached assessments to trigger recalculation with new defaults
    if "edited_assessments" in st.session_state:
        del st.session_state["edited_assessments"]

    st.success("Settings saved! Assessments will refresh with new defaults.")