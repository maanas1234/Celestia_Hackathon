# backend/server.py
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os
from datetime import datetime

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

ALERT_DIR = "alerts"
os.makedirs(ALERT_DIR, exist_ok=True)

# keep simple in-memory latest alert metadata
latest_alert = {}

@app.post("/alert")
async def receive_alert(frame: UploadFile = File(...), alert: str = Form(...),
                        men: str = Form(...), women: str = Form(...), time: str = Form(None)):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"alert_{ts}.jpg"
    path = os.path.join(ALERT_DIR, filename)
    content = await frame.read()
    with open(path, "wb") as f:
        f.write(content)

    meta = {
        "alert": alert,
        "men": int(men),
        "women": int(women),
        "time": time or datetime.now().isoformat(),
        "image_path": path
    }
    global latest_alert
    latest_alert = meta
    print("Received alert:", meta)
    return JSONResponse({"status":"ok", "saved": filename})

@app.get("/latest")
def get_latest():
    global latest_alert
    if not latest_alert:
        return JSONResponse({"status":"none"})
    # serve image as URL path for frontend; Streamlit can request via backend endpoint
    return JSONResponse({
        "status": "ok",
        "alert": latest_alert["alert"],
        "men": latest_alert["men"],
        "women": latest_alert["women"],
        "time": latest_alert["time"],
        "image_url": f"/image/{os.path.basename(latest_alert['image_path'])}"
    })

@app.get("/image/{imgname}")
def get_image(imgname: str):
    path = os.path.join(ALERT_DIR, imgname)
    if os.path.exists(path):
        return FileResponse(path, media_type="image/jpeg")
    return JSONResponse({"error":"not found"}, status_code=404)
