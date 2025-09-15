import os
import pandas as pd

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
EXPORT_DIR = os.path.join(BASE_DIR, "attendance_exports")
os.makedirs(EXPORT_DIR, exist_ok=True)

EXPORT_FILE = os.path.join(EXPORT_DIR, "attendance.xlsx")

def save_attendance_to_excel(session_id, class_name, student_name, student_id):
    """Append or create attendance Excel file"""
    record = {
        "Session ID": session_id,
        "Class Name": class_name,
        "Student ID": student_id,
        "Student Name": student_name,
        "Marked At": pd.Timestamp.now()
    }

    # If file exists → append, else create
    if os.path.exists(EXPORT_FILE):
        df = pd.read_excel(EXPORT_FILE)
        df = pd.concat([df, pd.DataFrame([record])], ignore_index=True)
    else:
        df = pd.DataFrame([record])

    df.to_excel(EXPORT_FILE, index=False)
