# server.py
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from datetime import datetime
import cloudinary
import cloudinary.uploader
import os
from dotenv import load_dotenv
from datetime import timezone

load_dotenv()
#"timestamp": datetime.now(timezone.utc)

# ---------------- CONFIG ----------------
MONGO_URI = os.getenv("MONGO_URI")
CLOUD_NAME = os.getenv("CLOUD_NAME")
API_KEY = os.getenv("CLOUD_API_KEY")
API_SECRET = os.getenv("CLOUD_API_SECRET")
DB_NAME = "women_safety"
COLLECTION_NAME = "alerts"
# ---------------------------------------

# MongoDB client
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
alerts_col = db[COLLECTION_NAME]

# Cloudinary config
cloudinary.config(
    cloud_name=CLOUD_NAME,
    api_key=API_KEY,
    api_secret=API_SECRET
)

# FastAPI app
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For hackathon/demo
    allow_methods=["*"],
    allow_headers=["*"]
)

# POST alert from camera
@app.post("/alert")
async def post_alert(
    alert: str = Form(...),
    men: int = Form(...),
    women: int = Form(...),
    frame: UploadFile = File(...)
):
    # Save frame to Cloudinary
    contents = await frame.read()
    result = cloudinary.uploader.upload(
    contents,
    folder="women_safety_alerts",
    public_id=f"alert_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
)

    img_url = result.get("secure_url")

    # Save to MongoDB
    alert_doc = {
        "timestamp": datetime.now(),
        "men_count": men,
        "women_count": women,
        "alert_text": alert,
        "image_url": img_url
    }
    alerts_col.insert_one(alert_doc)
    return {"status": "success", "image_url": img_url}

# GET latest alerts
@app.get("/alerts/latest")
def get_latest(limit: int = 10):
    data = list(alerts_col.find().sort("timestamp", -1).limit(limit))
    for d in data:
        d["_id"] = str(d["_id"])
        d["timestamp"] = d["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
    return data
