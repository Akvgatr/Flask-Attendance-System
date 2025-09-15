import math
import os
from datetime import datetime, timezone as dt_timezone   # datetime's timezone
from flask import Blueprint, request, jsonify, send_file
from .extensions import db
from .models import Session, Attendance, User
from sqlalchemy.exc import IntegrityError
import requests
from .services import attendance_excel
from pytz import timezone as pytz_timezone   # pytz timezone

api_bp = Blueprint("api", __name__)
IST = pytz_timezone("Asia/Kolkata")   # Indian Standard Time

# -----------------------------
# Helpers
# -----------------------------
def as_utc(dt: datetime) -> datetime:
    """Return a timezone-aware UTC datetime."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=dt_timezone.utc)
    return dt.astimezone(dt_timezone.utc)

def iso_utc(dt: datetime) -> str:
    """Serialize datetime to ISO 8601 UTC with trailing Z."""
    return as_utc(dt).isoformat().replace("+00:00", "Z")

def parse_ts(v):
    """Parse ms timestamps or ISO strings → UTC datetime."""
    if isinstance(v, (int, float)):
        return datetime.fromtimestamp(v/1000, tz=dt_timezone.utc)
    if not isinstance(v, str):
        raise ValueError("timestamp must be number or ISO string")
    dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
    return as_utc(dt)

# -----------------------------
# Sessions
# -----------------------------
from flask_login import current_user, login_required

# -----------------------------
# Sessions (filtered by teacher)
# -----------------------------
@api_bp.get("/sessions")
@login_required
def list_sessions():
    """Return sessions only for the logged-in teacher if they are a teacher."""
    if current_user.role == "teacher":
        q = Session.query.filter_by(teacher_id=current_user.id).order_by(Session.start_ts.desc())
    else:
        # For admins or students, you could return all or empty
        q = Session.query.order_by(Session.start_ts.desc())

    out = [{
        "id": s.id,
        "teacher_id": s.teacher_id,
        "class_name": s.class_name,
        "start_ts": iso_utc(s.start_ts),
        "end_ts": iso_utc(s.end_ts),
        "lat": s.lat,
        "lng": s.lng,
        "radius_m": s.radius_m
    } for s in q.all()]

    return jsonify(out)

@api_bp.post("/sessions")
def create_session():
    data = request.get_json(silent=True) or {}
    for field in ("teacher_id", "class_name", "start_ts", "end_ts"):
        if data.get(field) in (None, "", []):
            return jsonify({"error": f"missing field: {field}"}), 400

    try:
        teacher_id = int(data["teacher_id"])
    except Exception:
        return jsonify({"error": "teacher_id must be an integer"}), 400

    try:
        start_local = parse_ts(data["start_ts"]).astimezone(IST)
        end_local   = parse_ts(data["end_ts"]).astimezone(IST)
        start = start_local.astimezone(dt_timezone.utc)
        end   = end_local.astimezone(dt_timezone.utc)
    except Exception:
        return jsonify({"error": "bad timestamp format (use ISO or ms)"}), 400

    if end <= start:
        return jsonify({"error": "end must be after start"}), 400

    class_name = str(data["class_name"]).strip()
    if not class_name:
        return jsonify({"error": "class_name cannot be blank"}), 400

    s = Session(
        teacher_id = teacher_id,
        class_name = class_name,
        start_ts   = start,
        end_ts     = end,
        lat        = data.get("lat"),
        lng        = data.get("lng"),
        radius_m   = data.get("radius_m"),
    )
    db.session.add(s)
    db.session.commit()
    return jsonify({"id": s.id}), 201

@api_bp.put("/sessions/<int:sid>")
def update_session(sid):
    s = Session.query.get_or_404(sid)
    data = request.get_json(silent=True) or {}

    if "class_name" in data:
        name = str(data["class_name"]).strip()
        if not name:
            return jsonify({"error": "class_name cannot be blank"}), 400
        s.class_name = name

    if "teacher_id" in data:
        try:
            s.teacher_id = int(data["teacher_id"])
        except Exception:
            return jsonify({"error": "teacher_id must be an integer"}), 400

    if "start_ts" in data:
        try:
            s.start_ts = parse_ts(data["start_ts"]).astimezone(dt_timezone.utc)
        except Exception:
            return jsonify({"error": "bad start_ts"}), 400
    if "end_ts" in data:
        try:
            s.end_ts = parse_ts(data["end_ts"]).astimezone(dt_timezone.utc)
        except Exception:
            return jsonify({"error": "bad end_ts"}), 400
    if s.end_ts <= s.start_ts:
        return jsonify({"error": "end must be after start"}), 400

    if "lat" in data: s.lat = data.get("lat")
    if "lng" in data: s.lng = data.get("lng")
    if "radius_m" in data: s.radius_m = data.get("radius_m")

    db.session.commit()
    return jsonify({"ok": True})

@api_bp.delete("/sessions/<int:sid>")
def delete_session(sid):
    s = Session.query.get_or_404(sid)
    db.session.delete(s)
    db.session.commit()
    return jsonify({"ok": True})

@api_bp.get("/sessions/<int:sid>/attendance_count")
def attendance_count(sid):
    count = Attendance.query.filter_by(session_id=sid).count()
    return jsonify({"count": count})

# -----------------------------
# Attendance
# -----------------------------
@api_bp.get("/attendance")
def list_attendance():
    student_id = request.args.get("student_id", type=int)
    session_id = request.args.get("session_id", type=int)
    q = Attendance.query
    if student_id is not None:
        q = q.filter_by(student_id=student_id)
    if session_id is not None:
        q = q.filter_by(session_id=session_id)
    out = [{
        "id": a.id,
        "session_id": a.session_id,
        "student_id": a.student_id,
        "marked_at": iso_utc(a.marked_at) if getattr(a, "marked_at", None) else None,
        "speech_ok": a.speech_ok,
        "face_ok": a.face_ok,
        "geo_ok": a.geo_ok,
    } for a in q.order_by(Attendance.id.desc()).all()]
    return jsonify(out)

@api_bp.post("/attendance")
def mark_attendance():
    data = request.get_json(silent=True) or {}
    for f in ("session_id", "student_id"):
        if data.get(f) in (None, "", []):
            return jsonify({"error": f"missing field: {f}"}), 400

    try:
        session_id = int(data["session_id"])
        student_id = int(data["student_id"])
    except Exception:
        return jsonify({"error": "session_id and student_id must be integers"}), 400

    s = Session.query.get_or_404(session_id)
    student = User.query.filter_by(student_id=student_id, role="student").first()
    if not student:
        return jsonify({"error": "Student not found"}), 404

    # geofence check
    if s.lat is not None and s.lng is not None and s.radius_m is not None:
        lat = data.get("lat")
        lng = data.get("lng")
        if lat is None or lng is None:
            return jsonify({"error": "geolocation required for this session"}), 400
        try:
            dist = haversine_m(float(s.lat), float(s.lng), float(lat), float(lng))
        except Exception:
            return jsonify({"error": "bad_coordinates"}), 400
        if dist > float(s.radius_m):
            return jsonify({"error": f"outside_radius:{round(dist)}"}), 400

    a = Attendance(
        session_id = session_id,
        student_id = student.id,
        speech_ok  = bool(data.get("speech_ok", False)),
        face_ok    = bool(data.get("face_ok", False)),
        geo_ok     = True,
    )
    db.session.add(a)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Already marked or invalid"}), 400

    # Update Excel
    attendance_excel.save_attendance_to_excel(
        session_id=s.id,
        class_name=s.class_name,
        student_name=student.name,
        student_id=student.student_id
    )

    return jsonify({"ok": True, "id": a.id, "message": "Attendance marked & Excel updated"}), 201

# -----------------------------
# Attendance Export
# -----------------------------
@api_bp.get("/export_attendance")
def export_attendance():
    if not os.path.exists(attendance_excel.EXPORT_FILE):
        return jsonify({"error": "No attendance file found"}), 404
    return send_file(attendance_excel.EXPORT_FILE, as_attachment=True)

# -----------------------------
# Utils
# -----------------------------
def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000.0
    to_rad = math.pi / 180.0
    dlat = (lat2 - lat1) * to_rad
    dlon = (lon2 - lon1) * to_rad
    a = math.sin(dlat/2)**2 + math.cos(lat1*to_rad) * math.cos(lat2*to_rad) * math.sin(dlon/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def get_public_ip():
    r = requests.get("http://api.ipify.org", timeout=2)
    r.raise_for_status()
    return r.text.strip()

def ip_proxy_flag(ip: str):
    url = f"http://ip-api.com/json/{ip}?fields=proxy,hosting,status,message"
    try:
        r = requests.get(url, timeout=2)
        r.raise_for_status()
        data = r.json()
        if data.get("status") != "success":
            return False, data.get("message", "lookup_failed")
        return bool(data.get("proxy") or data.get("hosting")), None
    except Exception as e:
        return False, str(e)
