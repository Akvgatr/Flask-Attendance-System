import os
import cv2
import numpy as np
import face_recognition
from cvzone.FaceMeshModule import FaceMeshDetector


# --- Blink function (yours, unchanged) ---
def is_blinking(face, detector, ratio_list, counter, threshold=32, cooldown=10):
    leftUp = face[159]
    leftDown = face[23]
    leftLeft = face[130]
    leftRight = face[243]

    vertical_len, _ = detector.findDistance(leftUp, leftDown)
    horizontal_len, _ = detector.findDistance(leftLeft, leftRight)

    if horizontal_len == 0:
        return False, ratio_list, counter

    ratio = (vertical_len / horizontal_len) * 100
    ratio_list.append(ratio)
    if len(ratio_list) > 5:
        ratio_list.pop(0)
    ratio_avg = sum(ratio_list) / len(ratio_list)

    blink_detected = False
    if ratio_avg < threshold and counter == 0:
        blink_detected = True
        counter = 1
    if counter != 0:
        counter += 1
        if counter > cooldown:
            counter = 0

    return blink_detected, ratio_list, counter


# --- Registration with blink verification ---
def register_face_with_blink(student_id: str, max_embeddings: int = 5, camera_index: int = 0):
    save_dir = os.path.join(os.path.dirname(__file__), f"face_data/{student_id}")
    os.makedirs(save_dir, exist_ok=True)

    cap = cv2.VideoCapture(camera_index)
    detector = FaceMeshDetector(maxFaces=1)

    count = 0
    ratio_list = []
    blink_counter = 0
    capture_ready = False

    print("Blink once, then open eyes to capture embedding... (ESC to quit)")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                return {"ok": False, "message": "Failed to read camera frame."}

            frame, faces = detector.findFaceMesh(frame, draw=False)

            if faces:
                face = faces[0]
                blink, ratio_list, blink_counter = is_blinking(face, detector, ratio_list, blink_counter)

                if blink:
                    capture_ready = True
                elif capture_ready:
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    boxes = face_recognition.face_locations(rgb_frame)

                    if boxes:
                        encodings = face_recognition.face_encodings(rgb_frame, boxes)
                        for encoding in encodings:
                            npy_path = os.path.join(save_dir, f"face_{count}.npy")
                            np.save(npy_path, encoding)
                            print(f"[Saved] {npy_path}")
                            count += 1
                            capture_ready = False

                            if count >= max_embeddings:
                                cap.release()
                                cv2.destroyAllWindows()
                                return {"ok": True, "message": f"Collected {max_embeddings} embeddings.",
                                        "path": save_dir}
                    else:
                        print("Face not detected clearly.")

            cv2.imshow("Blink to Capture", frame)
            if cv2.waitKey(1) & 0xFF == 27:
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()

    return {"ok": True, "message": f"Collected {count} embeddings.", "path": save_dir}
