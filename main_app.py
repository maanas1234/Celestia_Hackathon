import cv2
import numpy as np
from ultralytics import YOLO
from datetime import datetime
import requests
import os

# ---------------- SETTINGS ----------------
CONF_THRESH = 0.5
MAX_WIDTH = 640
ALERT_ENDPOINT = "http://127.0.0.1:8000/alert"  # Replace with your backend URL
# ------------------------------------------

# YOLO model
yolo_model = YOLO("../models/yolov8n.pt")

# Gender model
gender_net = cv2.dnn.readNetFromCaffe(
    "../models/gender_deploy.prototxt",
    "../models/gender_net.caffemodel"
)
GENDER_LIST = ["Male", "Female"]

# Webcam
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    raise Exception("Cannot open webcam")

print("👮 Women Safety Monitoring Running... Press 'q' to exit.")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    h, w = frame.shape[:2]
    scale = MAX_WIDTH / w
    frame = cv2.resize(frame, (MAX_WIDTH, int(h*scale)))

    results = yolo_model(frame, conf=CONF_THRESH, verbose=False)
    boxes = results[0].boxes.xyxy.cpu().numpy()
    labels = results[0].boxes.cls.cpu().numpy()

    men_count = 0
    women_count = 0

    for (x1, y1, x2, y2), label in zip(boxes, labels):
        if int(label) != 0:  # 0 = person
            continue

        face = frame[int(y1):int(y2), int(x1):int(x2)]
        if face.size == 0:
            continue

        blob = cv2.dnn.blobFromImage(face, 1.0, (227,227),
                                     (78.4263377603,87.7689143744,114.895847746),
                                     swapRB=False)
        gender_net.setInput(blob)
        preds = gender_net.forward()
        gender = GENDER_LIST[preds[0].argmax()]

        if gender == "Male":
            men_count += 1
            color = (255,0,0)
        else:
            women_count += 1
            color = (0,0,255)

        cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
        cv2.putText(frame, gender, (int(x1), int(y1)-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

    # Alert logic
    alert = None
    hour = datetime.now().hour
    if women_count == 1 and men_count >= 2:
        alert = "🚨 Single woman with multiple men 🚨"
    elif women_count == 1 and hour >= 20:
        alert = "🌙 Single woman at night 🚨"

    if alert:
        cv2.putText(frame, alert, (10,30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255),3)
        _, img_encoded = cv2.imencode('.jpg', frame)
        try:
            requests.post(ALERT_ENDPOINT, files={"frame": img_encoded.tobytes()},
                          data={"alert": alert, "men": men_count, "women": women_count})
        except Exception as e:
            print("Failed to send alert:", e)

    cv2.imshow("Women Safety Monitoring", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
