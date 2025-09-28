# camera_app/main_app.py
import cv2
import numpy as np
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import onnxruntime as ort
from PIL import Image
from torchvision import transforms

# ---------------- SETTINGS ----------------
ALERT_ENDPOINT = "http://127.0.0.1:8000/alert"   # Backend FastAPI URL
CONF_THRESH = 0.5
MAX_WIDTH = 400
FRAME_SKIP = 3
executor = ThreadPoolExecutor(max_workers=2)
MODEL_PATH = "model.onnx"
# ------------------------------------------

# Load Haar cascade
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

# Load ONNX model
gender_sess = ort.InferenceSession(MODEL_PATH)
input_name = gender_sess.get_inputs()[0].name

# Torchvision transform (match your training preprocessing)
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

def predict_gender(face_img):
    try:
        img = Image.fromarray(cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB))
        img = transform(img).unsqueeze(0).numpy().astype(np.float32)
        pred = gender_sess.run(None, {input_name: img})[0]
        return "Female" if np.argmax(pred) == 0 else "Male"
    except Exception as e:
        print("Gender prediction failed:", e)
        return "Unknown"

def send_alert_file(img_bytes, men, women, alert_text):
    try:
        files = {"frame": ("frame.jpg", img_bytes, "image/jpeg")}
        data = {"alert": alert_text or "", "men": str(men), "women": str(women)}
        r = requests.post(ALERT_ENDPOINT, files=files, data=data, timeout=4)
        r.raise_for_status()
        print("✅ Alert sent:", r.status_code)
    except Exception as e:
        print("❌ Failed to send alert:", e)

# Start camera
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    raise Exception("Cannot open webcam")

frame_count = 0
last_boxes, last_genders = [], []

print("👮 Women Safety Monitoring Running... Press 'q' to exit.")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame_count += 1
    h, w = frame.shape[:2]
    scale = MAX_WIDTH / float(w)
    frame_small = cv2.resize(frame, (MAX_WIDTH, int(h * scale)))

    boxes, genders = [], []

    if frame_count % FRAME_SKIP == 0:
        gray = cv2.cvtColor(frame_small, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

        for (x, y, fw, fh) in faces:
            face_img = frame_small[y:y+fh, x:x+fw]
            gender = predict_gender(face_img)
            boxes.append((x, y, x + fw, y + fh))
            genders.append(gender)

        last_boxes, last_genders = boxes, genders
    else:
        boxes, genders = last_boxes, last_genders

    men_count = sum(1 for g in genders if g == "Male")
    women_count = sum(1 for g in genders if g == "Female")

    # Draw boxes
    for (x1, y1, x2, y2), g in zip(boxes, genders):
        color = (255, 0, 0) if g == "Male" else (0, 0, 255) if g == "Female" else (0, 255, 0)
        cv2.rectangle(frame_small, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame_small, g, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    # Alert rules
    alert_text = None
    hour = datetime.now().hour
    if women_count == 1 and men_count >= 2:
        alert_text = "🚨 Single woman with multiple men 🚨"
    elif women_count == 1 and hour >= 20:
        alert_text = "🌙 Single woman at night 🚨"

    if alert_text:
        cv2.putText(frame_small, alert_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        _, jpg = cv2.imencode('.jpg', frame_small)
        img_bytes = jpg.tobytes()
        executor.submit(send_alert_file, img_bytes, men_count, women_count, alert_text)

    cv2.imshow("Women Safety Monitoring", frame_small)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
executor.shutdown(wait=False)
