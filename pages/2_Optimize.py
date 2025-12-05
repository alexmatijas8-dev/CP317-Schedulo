import streamlit as st
import pandas as pd
from backend.schedule import ScheduleOptimizer
from utils.normalize import normalize_type
from backend.sb_functions import save_schedule, remove_course, save_courses

# Stop if user not logged in

if "uid" not in st.session_state or not st.session_state["uid"]:
    st.error("You must be logged in to access this page.")
    st.stop()

st.set_page_config(layout="wide")
st.title("Optimize Study Plan")

# Validate required data exists
if "courses" not in st.session_state or not st.session_state["courses"]:
    st.error("No courses found. Upload syllabi first.")
    st.stop()

if "settings" not in st.session_state:
    st.error("Settings not found. Configure them first.")
    st.stop()

courses = st.session_state["courses"]
settings = st.session_state["settings"]

daily_hours = settings.get("daily_hours", {})
work_ahead_days = settings.get("work_ahead_days", {})
base_hours = settings.get("base_hours", {})
semester_start = settings.get("semester_start")
semester_end = settings.get("semester_end")

if not semester_start or not semester_end:
    st.error("Semester dates not found. Go to Upload or Settings page and set them first.")
    st.stop()

# Initialize assessments from courses using current settings
if "edited_assessments" not in st.session_state:
    all_assessments = []
    for course_json in courses.values():
        course_code = course_json.get("course_info", {}).get("course_code", "")
        breakdown = course_json.get("assessments", {}).get("breakdown", [])
        for a in breakdown:
            raw_type = a.get("type", "")
            atype = normalize_type(raw_type)
            entry = {
                "course_code": course_code,
                "type": atype,
                "title": a.get("title") or raw_type.title(),
                "due_date": a.get("due_date"),
                "hours_required": base_hours.get(atype, 0),
                "work_ahead_days": work_ahead_days.get(atype, 0)
            }
            all_assessments.append(entry)
    st.session_state["edited_assessments"] = all_assessments
    st.session_state["original_assessments"] = [a.copy() for a in all_assessments]
else:
    all_assessments = st.session_state["edited_assessments"]
    if "original_assessments" not in st.session_state:
        st.session_state["original_assessments"] = [a.copy() for a in all_assessments]

st.subheader("Filter by Course")

# Course filter dropdown
course_list = ["All Courses"] + list(courses.keys())
selected_course = st.selectbox("Select a course to view:", course_list)

if selected_course != "All Courses":
    filtered_assessments = [a for a in all_assessments if a["course_code"] == selected_course]
else:
    filtered_assessments = all_assessments

# Prepare dataframe for editing
df = pd.DataFrame(filtered_assessments)
df_display = df.drop(columns=["work_ahead_days"])

st.subheader("Edit Assessments (Optional)")
st.write("You can edit hours, due dates, add or delete assessments")

# Editable assessment table
edited_df = st.data_editor(
    df_display,
    hide_index=True,
    use_container_width=True,
    num_rows="dynamic",
    column_config={
        "course_code": st.column_config.SelectboxColumn(
            "Course",
            options=list(courses.keys()),
            required=False
        ),
        "type": st.column_config.TextColumn("Type", required=False),
        "title": st.column_config.TextColumn("Title", required=False),
        "due_date": st.column_config.TextColumn(
            "Due Date (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)",
            required=False
        ),
        "hours_required": st.column_config.NumberColumn(
            "Hours Required",
            min_value=0,
            max_value=500,
            step=1,
            format="%d",
            required=False
        )
    },
    key="assessment_editor"
)

# Restore work_ahead_days to edited assessments
updated_assessments = edited_df.to_dict(orient="records")

for i, row in enumerate(updated_assessments):
    if i < len(filtered_assessments):
        row["work_ahead_days"] = filtered_assessments[i]["work_ahead_days"]
    else:
        atype = normalize_type(row.get("type", ""))
        row["work_ahead_days"] = work_ahead_days.get(atype, 0)

# Merge filtered changes back into full assessment list
if selected_course != "All Courses":
    other_assessments = [
        a for a in st.session_state["edited_assessments"]
        if a["course_code"] != selected_course
    ]
    updated_assessments = other_assessments + updated_assessments

st.session_state["edited_assessments"] = updated_assessments

# Check for unsaved changes
has_changes = False
original = st.session_state.get("original_assessments", [])

if len(updated_assessments) != len(original):
    has_changes = True
else:
    for curr, orig in zip(updated_assessments, original):
        if (curr.get("course_code") != orig.get("course_code") or
            curr.get("type") != orig.get("type") or
            curr.get("title") != orig.get("title") or
            curr.get("due_date") != orig.get("due_date") or
            curr.get("hours_required") != orig.get("hours_required")):
            has_changes = True
            break

if has_changes:
    st.warning("You have unsaved changes in the assessment table. Click 'Save Changes' below to apply them.")

col1, col2 = st.columns(2)

# Save changes button
with col1:
    if st.button("Save Changes", use_container_width=True):
        # Group assessments by course
        course_assessments = {}
        for assessment in updated_assessments:
            course_code = assessment["course_code"]
            if course_code not in course_assessments:
                course_assessments[course_code] = []
            course_assessments[course_code].append({
                "type": str(assessment.get("type") or ""),
                "title": str(assessment.get("title") or ""),
                "due_date": assessment.get("due_date") or None,
                "hours_required": int(assessment.get("hours_required") or 0),
                "work_ahead_days": int(assessment.get("work_ahead_days") or 0)
            })
        
        # Update courses in session state
        for course_code, assessments_list in course_assessments.items():
            if course_code in st.session_state["courses"]:
                if "assessments" not in st.session_state["courses"][course_code]:
                    st.session_state["courses"][course_code]["assessments"] = {}
                st.session_state["courses"][course_code]["assessments"]["breakdown"] = assessments_list
        
        if "uid" in st.session_state:
            save_courses(st.session_state["uid"], st.session_state["courses"])
        
        st.session_state["original_assessments"] = [a.copy() for a in updated_assessments]
        
        st.success("Changes saved!")
        st.rerun()

# Remove course button
with col2:
    if selected_course != "All Courses":
        if st.button(f"Remove {selected_course}", type="secondary", use_container_width=True):
            if "uid" in st.session_state:
                remove_course(st.session_state["uid"], selected_course)
            del st.session_state["courses"][selected_course]
            if "edited_assessments" in st.session_state:
                del st.session_state["edited_assessments"]
            if "original_assessments" in st.session_state:
                del st.session_state["original_assessments"]
            st.success(f"{selected_course} removed!")
            st.rerun()

st.divider()

# Generate schedule
if st.button("Generate Study Plan", type="primary", use_container_width=True):
    optimizer = ScheduleOptimizer(
        semester_start=semester_start,
        semester_end=semester_end,
        daily_hours=daily_hours,
        work_ahead_days=work_ahead_days
    )
    schedule = optimizer.generate_raw_schedule(updated_assessments)
    
    allocations = schedule.get("allocations", [])
    
    # Find assessments with scheduling problems
    problems = []
    for idx, allocation in enumerate(allocations):
        if idx < len(updated_assessments):
            assessment = updated_assessments[idx]
            scheduled = allocation.get("scheduled_hours", 0)
            unscheduled = allocation.get("unscheduled_hours", 0)
            status = allocation.get("status", "unknown")
            required = assessment.get("hours_required", 0)
            
            if unscheduled > 0.25 or status != "ok":
                problems.append({
                    'course': assessment.get('course_code', 'Unknown'),
                    'title': assessment.get('title', 'Unknown'),
                    'type': assessment.get('type', 'Unknown'),
                    'due_date': assessment.get('due_date', 'Unknown'),
                    'required': required,
                    'scheduled': scheduled,
                    'unscheduled': unscheduled,
                    'status': status
                })
    
    # Display scheduling warnings if any
    if problems:
        st.warning(f"Warning: {len(problems)} assessment(s) could not be fully scheduled!")
        with st.expander("View scheduling issues"):
            for p in problems:
                if p['scheduled'] == 0:
                    st.write(f"**{p['course']}**: {p['title']} ({p['type']}) - Due: {p['due_date']}")
                    st.write(f"   Not scheduled at all - needs {p['required']} hours")
                    if p['status'] == 'skipped_missing_date_or_zero_hours':
                        st.write(f"    Reason: Missing due date or zero hours required")
                    elif p['status'] == 'no_available_days':
                        st.write(f"      Reason: No available study days in the work window")
                else:
                    st.write(f"**{p['course']}**: {p['title']} ({p['type']}) - Due: {p['due_date']}")
                    st.write(f"   Only {p['scheduled']:.1f} of {p['required']:.1f} hours scheduled (missing {p['unscheduled']:.1f} hours)")
    
    st.session_state["schedule"] = schedule
    if "uid" in st.session_state:
        save_schedule(st.session_state["uid"], schedule)
    
    if problems:
        fully_scheduled = len(updated_assessments) - len(problems)
        st.success(f"Schedule generated: {fully_scheduled}/{len(updated_assessments)} assessments fully scheduled. Review warnings above.")
    else:
        st.success(f"All {len(updated_assessments)} assessments successfully scheduled! Redirecting...")
        st.switch_page("pages/3_Calendar.py")