import os
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from . import db
from .models import User
from .services.authentication.face_verification import face_recg_blink, face_recog
from .services.authentication.speech_verification import register_voice
from .services import attendance_excel
from .models import Attendance, Session

web_bp = Blueprint("web", __name__)

# ------------------ Pages ------------------ #
@web_bp.get("/")
def index():
    return render_template("index.html")

@web_bp.get("/student/register")
def student_registration():
    return render_template("student_registration.html")

@web_bp.get("/teacher/register")
def teacher_registration():
    return render_template("teacher_registration.html")

@web_bp.get("/teacher")
@login_required
def teacher_dashboard():
    return render_template("teacher_dashboard.html")

@web_bp.get("/student")
@login_required
def student_dashboard():
    return render_template("student_dashboard.html")

@web_bp.get("/teacher/login")
def teacher_login():
    return render_template("teacher_login.html")

@web_bp.get("/student/login")
def student_login():
    return render_template("student_login.html")

@web_bp.get("/geolocation")
def geolocation():
    return render_template("geolocation.html")


# ------------------ Student Registration ------------------ #
@web_bp.post("/student/register")
def student_register_post():
    """Register student and directly log in"""
    student_id = request.form.get("student_id")
    username   = request.form.get("username")
    password   = request.form.get("password")
    email      = request.form.get("email")

    # Prevent duplicate
    if User.query.filter_by(student_id=student_id).first():
        flash("Student ID already exists.", "danger")
        return redirect(url_for("web.student_registration"))

    password_hash = generate_password_hash(password)
    new_student = User(
        role="student",
        student_id=student_id,
        name=username,
        email=email,
        password_hash=password_hash
    )
    db.session.add(new_student)
    db.session.commit()

    # Direct login
    login_user(new_student)
    flash("Registration successful! Welcome to your dashboard.", "success")
    return redirect(url_for("web.student_dashboard"))


# ------------------ Teacher Registration ------------------ #
@web_bp.post("/teacher/register")
def teacher_register_post():
    teacher_id = request.form.get("teacher_id")
    username   = request.form.get("username")
    password   = request.form.get("password")
    email      = request.form.get("email")

    if User.query.filter_by(student_id=teacher_id, role="teacher").first():
        flash("Teacher ID already exists.", "danger")
        return redirect(url_for("web.teacher_registration"))

    password_hash = generate_password_hash(password)
    new_teacher = User(
        role="teacher",
        student_id=teacher_id,
        name=username,
        email=email,
        password_hash=password_hash
    )
    db.session.add(new_teacher)
    db.session.commit()

    login_user(new_teacher)
    flash("Registration successful! Welcome to the teacher dashboard.", "success")
    return redirect(url_for("web.teacher_dashboard"))


# ------------------ Login APIs ------------------ #
@web_bp.post("/student/login")
def student_login_post():
    student_id = request.form.get("student_id")
    password   = request.form.get("password")

    user = User.query.filter_by(student_id=student_id, role="student").first()
    if not user or not check_password_hash(user.password_hash, password):
        flash("Invalid Student ID or Password", "danger")
        return redirect(url_for("web.student_login"))

    login_user(user)
    return redirect(url_for("web.student_dashboard"))

@web_bp.post("/teacher/login")
def teacher_login_post():
    email    = request.form.get("email")
    password = request.form.get("password")

    user = User.query.filter_by(email=email, role="teacher").first()
    if not user or not check_password_hash(user.password_hash, password):
        flash("Invalid Email or Password", "danger")
        return redirect(url_for("web.teacher_login"))

    login_user(user)
    return redirect(url_for("web.teacher_dashboard"))


# ------------------ Verification APIs ------------------ #
@web_bp.get("/face_register_blink")
def face_register_blink():
    student_id = request.args.get("id")
    result = face_recg_blink.register_face_with_blink(student_id)
    return jsonify(result)

@web_bp.get("/speech_phrase")
def speech_phrase():
    """Generate phrase for speech *enrollment*"""
    phrase = register_voice.get_random_phrase()
    return jsonify({"phrase": phrase})

@web_bp.post("/speech_register")
def speech_register():
    """Enroll student speech"""
    student_id = request.args.get("id")
    phrase = request.args.get("phrase")

    if not phrase:
        return jsonify({"ok": False, "message": "Missing phrase"})

    result = register_voice.register_student(student_id, phrase)
    return jsonify(result or {"ok": False, "message": "Speech registration failed"})

@web_bp.get("/face_verif")
def face_verif():
    """Verify student's face"""
    result = face_recog.verify_face(threshold=0.5)
    return jsonify(result)

@web_bp.get("/speech_verif_phrase")
def speech_verif_phrase():
    """Get phrase for speech *verification*"""
    phrase = register_voice.get_random_phrase()
    return jsonify({"phrase": phrase})

@web_bp.post("/speech_verif")
def speech_verif():
    """Verify student's speech with a fresh recording"""
    student_id = request.args.get("id") or (current_user.student_id if current_user.is_authenticated else None)
    phrase = request.args.get("phrase")

    if not student_id:
        return jsonify({"ok": False, "message": "No student ID"})
    if not phrase:
        return jsonify({"ok": False, "message": "Missing phrase"})

    result = register_voice.verify_student(student_id, phrase)

    # --- FIX: ensure Python native bool ---
    if result and "ok" in result:
        result["ok"] = bool(result["ok"])   # convert np.bool_ → bool

    return jsonify(result or {"ok": False, "message": "Speech verification failed"})



#----------------Attendance ------------------#
@web_bp.post("/api/attendance")
@login_required
def mark_attendance():
    """
    Student marks attendance:
    - Saves in DB
    - Updates Excel file
    """
    data = request.get_json()
    session_id = data.get("session_id")
    student_id = data.get("student_id")

    # --- Safety checks ---
    if not session_id or not student_id:
        return jsonify({"ok": False, "message": "Missing session_id or student_id"}), 400

    session = Session.query.get(session_id)
    if not session:
        return jsonify({"ok": False, "message": "Session not found"}), 404

    student = User.query.filter_by(student_id=student_id, role="student").first()
    if not student:
        return jsonify({"ok": False, "message": "Student not found"}), 404

    # --- Check if already marked ---
    existing = Attendance.query.filter_by(session_id=session_id, student_id=student.id).first()
    if existing:
        return jsonify({"ok": False, "message": "Already marked"}), 400

    # --- Save in DB ---
    new_attendance = Attendance(session_id=session_id, student_id=student.id)
    db.session.add(new_attendance)
    db.session.commit()

    # --- Update Excel ---
    attendance_excel.save_attendance_to_excel(
        session_id=session.id,
        class_name=session.class_name,
        student_name=student.name,
        student_id=student.student_id
    )

    return jsonify({"ok": True, "message": "Attendance marked successfully"})

# ------------------ Logout ------------------ #
@web_bp.get("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("web.index"))

