import os
import time
import cv2
import numpy as np
import face_recognition as fr

# ---------- paths ----------
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "face_data")
os.makedirs(DATA_DIR, exist_ok=True)

# ---------- load encodings once ----------
known_encodings, known_names = [], []
if os.path.isdir(DATA_DIR):
    for person in os.listdir(DATA_DIR):
        person_dir = os.path.join(DATA_DIR, person)
        if not os.path.isdir(person_dir):
            continue
        for file in os.listdir(person_dir):
            if file.endswith(".npy"):
                try:
                    enc = np.load(os.path.join(person_dir, file))
                    known_encodings.append(enc)
                    known_names.append(person)
                except Exception:
                    pass  # skip corrupt files

def _face_confidence(face_distance: float, threshold: float) -> float:
    rng = (1.0 - threshold)
    return round(((1.0 - face_distance) / (rng * 2.0)) * 100, 2)

# ---------- main API (returns dict) ----------
def verify_face(threshold: float = 0.5, camera_index: int = 0, timeout_sec: int = 10):
    """
    Opens the camera, looks for a single face, compares to known encodings,
    returns a JSON-serializable dict. Captures until a face is seen or timeout.
    """
    if not known_encodings:
        return {"ok": False, "name": "Unknown", "confidence": 0.0,
                "message": "No registered faces found. Please register first."}

    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        return {"ok": False, "name": "Unknown", "confidence": 0.0,
                "message": "Cannot access camera."}

    t0 = time.time()
    name, conf, msg = "Unknown", 0.0, "No face detected."
    ok = False

    try:
        while time.time() - t0 < timeout_sec:
            ret, frame = cap.read()
            if not ret:
                msg = "Failed to read frame."
                break

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            boxes = fr.face_locations(rgb)

            if not boxes:
                cv2.waitKey(1)
                continue

            # use the biggest face in frame
            box = max(boxes, key=lambda b: (b[2]-b[0]) * (b[1]-b[3]))  # (top,right,bottom,left)
            encs = fr.face_encodings(rgb, [box])
            if not encs:
                msg = "Face found but encoding failed."
                break

            enc = encs[0]
            dists = fr.face_distance(known_encodings, enc)
            j = int(np.argmin(dists))
            if dists[j] <= threshold:
                name = known_names[j]
                conf = _face_confidence(dists[j], threshold)
                ok, msg = True, "Face Verified."
            else:
                conf = _face_confidence(dists[j], threshold)
                msg = "Face Mismatch."

            break  # we got a decision (match or not)

        return {"ok": ok, "name": name, "confidence": conf, "message": msg}
    finally:
        cap.release()
        cv2.destroyAllWindows()

def register_face(student_id: str, camera_index: int = 0, timeout_sec: int = 10):
    """
    Captures a face from webcam and saves its encoding under face_data/<student_id>/.
    """
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        return {"ok": False, "message": "Cannot access camera."}

    t0 = time.time()
    try:
        while time.time() - t0 < timeout_sec:
            ret, frame = cap.read()
            if not ret:
                return {"ok": False, "message": "Failed to read frame."}

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            boxes = fr.face_locations(rgb)
            if not boxes:
                cv2.waitKey(1)
                continue

            box = max(boxes, key=lambda b: (b[2]-b[0]) * (b[1]-b[3]))
            encs = fr.face_encodings(rgb, [box])
            if not encs:
                return {"ok": False, "message": "Face found but encoding failed."}

            enc = encs[0]
            out_dir = os.path.join(DATA_DIR, student_id)
            os.makedirs(out_dir, exist_ok=True)
            out_path = os.path.join(out_dir, f"{int(time.time())}.npy")
            np.save(out_path, enc)

            # also update in-memory cache so it's available immediately
            known_encodings.append(enc)
            known_names.append(student_id)

            return {"ok": True, "message": "Face registered.", "path": out_path}

        return {"ok": False, "message": "Timed out waiting for a face."}
    finally:
        cap.release()
        cv2.destroyAllWindows()
