# backend/server.py
import os
import logging
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader

load_dotenv()  # loads .env in same directory if present

# ---------- CONFIG ----------
MONGO_URI = os.getenv("MONGO_URI")
CLOUD_NAME = os.getenv("CLOUD_NAME")
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
DB_NAME = os.getenv("DB_NAME", "women_safety")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "alerts")
# ----------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("server")

# Mongo client - try to connect but do not crash app import
alerts_col = None
try:
    if MONGO_URI:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        # attempt a quick ping
        client.server_info()
        db = client[DB_NAME]
        alerts_col = db[COLLECTION_NAME]
        logger.info("Connected to MongoDB")
    else:
        logger.warning("MONGO_URI not set. Alerts will not be saved to DB.")
except Exception as e:
    logger.exception("MongoDB connection failed: %s", e)
    alerts_col = None

# Cloudinary config (optional)
if CLOUD_NAME and API_KEY and API_SECRET:
    cloudinary.config(
        cloud_name=CLOUD_NAME,
        api_key=API_KEY,
        api_secret=API_SECRET
    )
    logger.info("Cloudinary configured")
else:
    logger.warning("Cloudinary not configured. Image uploads will be skipped.")

app = FastAPI(title="Women Safety Backend")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def root():
    return {"status": "ok", "message": "Women Safety backend"}

@app.get("/health")
def health():
    return {
        "status": "ok",
        "mongo_connected": bool(alerts_col),
        "cloudinary_configured": bool(CLOUD_NAME and API_KEY and API_SECRET)
    }

@app.post("/alert")
async def post_alert(
    alert: str = Form(None),
    men: int = Form(None),
    women: int = Form(None),
    frame: UploadFile = File(None)
):
    """
    Accepts multipart/form-data:
      - alert (str)
      - men (int)
      - women (int)
      - frame (file) optional
    """
    img_url = None

    # Upload image to Cloudinary if provided and configured
    if frame is not None:
        contents = await frame.read()
        if CLOUD_NAME and API_KEY and API_SECRET:
            try:
                res = cloudinary.uploader.upload(
                    contents,
                    folder="women_safety_alerts",
                    public_id=f"alert_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                    overwrite=True
                )
                img_url = res.get("secure_url")
            except Exception as e:
                logger.exception("Cloudinary upload failed: %s", e)
                # continue without crashing
        else:
            logger.warning("Frame received but Cloudinary not configured - skipping upload")

    # Build document
    doc = {
        "timestamp": datetime.utcnow(),
        "men_count": int(men) if men is not None else 0,
        "women_count": int(women) if women is not None else 0,
        "alert_text": alert or "",
        "image_url": img_url
    }

    # Save to Mongo if available
    if alerts_col:
        try:
            alerts_col.insert_one(doc)
        except Exception as e:
            logger.exception("Failed to insert alert into MongoDB: %s", e)
            raise HTTPException(status_code=500, detail="DB insert failed")
    else:
        logger.warning("No DB configured; alert not saved to DB: %s", doc)

    return {"status": "ok", "saved": bool(alerts_col), "image_url": img_url}

@app.get("/alerts/latest")
def get_latest(limit: int = 20):
    if not alerts_col:
        return []
    docs = list(alerts_col.find().sort("timestamp", -1).limit(limit))
    for d in docs:
        d["_id"] = str(d["_id"])
        d["timestamp"] = d["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
    return docs
