# src/demo/website/models.py
from datetime import datetime, timezone
from flask_login import UserMixin
from .extensions import db, login_manager

# ---------- User (Student + Teacher) ----------
class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)

    role = db.Column(db.String(16), nullable=False, default="student")
    # "student" or "teacher"

    student_id = db.Column(db.String(100), unique=True, nullable=True)
    # Only used if role == "student" (can be None for teachers)

    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    # relationships
    sessions = db.relationship(
        "Session",
        backref="teacher",        # for teacher users
        lazy=True,
        cascade="all,delete-orphan"
    )
    attendances = db.relationship(
        "Attendance",
        backref="student",        # for student users
        lazy=True,
        cascade="all,delete-orphan"
    )

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------- Session ----------
class Session(db.Model):
    __tablename__ = "sessions"
    id = db.Column(db.Integer, primary_key=True)

    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    # must point to a teacher user

    class_name = db.Column(db.String(200), nullable=False)

    start_ts = db.Column(db.DateTime, nullable=False)
    end_ts   = db.Column(db.DateTime, nullable=False)

    lat = db.Column(db.Float)
    lng = db.Column(db.Float)
    radius_m = db.Column(db.Float)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    attendance = db.relationship(
        "Attendance",
        backref="session",
        lazy=True,
        cascade="all,delete-orphan"
    )

# ---------- Attendance ----------
class Attendance(db.Model):
    __tablename__ = "attendances"
    id = db.Column(db.Integer, primary_key=True)

    session_id = db.Column(db.Integer, db.ForeignKey("sessions.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    marked_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    speech_ok = db.Column(db.Boolean, default=False, nullable=False)
    face_ok   = db.Column(db.Boolean, default=False, nullable=False)
    geo_ok    = db.Column(db.Boolean, default=False, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("session_id", "student_id", name="uq_mark_once"),
    )
