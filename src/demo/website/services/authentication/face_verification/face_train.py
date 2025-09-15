import cv2
import os
import numpy as np
import face_recognition
from cvzone.FaceMeshModule import FaceMeshDetector
from blink_detection import is_blinking

# Create user directory for storing embeddings
name = input("Enter your name: ").strip()
save_dir = os.path.join(os.path.dirname(__file__), f"face_data/{name}")
os.makedirs(save_dir, exist_ok=True)

cap = cv2.VideoCapture(0)
detector = FaceMeshDetector(maxFaces=1)

count = 0
max_embeddings = 20
ratio_list = []
blink_counter = 0
capture_ready = False

print("Blink once, then open eyes to capture embedding... (ESC to quit)")

while True:
    ret, frame = cap.read()
    if not ret:
        break

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
                        print(f"Collected {max_embeddings} embeddings. Exiting.")
                        cap.release()
                        cv2.destroyAllWindows()
                        exit()
            else:
                print("Face not detected clearly.")

    cv2.imshow("Blink to Capture", frame)
    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()