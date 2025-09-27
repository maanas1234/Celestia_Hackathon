import streamlit as st
import pandas as pd
import requests
from PIL import Image
from io import BytesIO

BACKEND_URL = "http://127.0.0.1:8000"

st.title("🚨 Women Safety Admin Dashboard")

st.info("Showing latest alerts from camera")

try:
    response = requests.get(f"{BACKEND_URL}/alerts/latest?limit=10")
    data = response.json()
except:
    st.error("Cannot fetch alerts. Check backend URL.")
    data = []

if data:
    for alert in data:
        st.subheader(alert["alert_text"])
        st.text(f"Time: {alert['timestamp']} | Men: {alert['men_count']} | Women: {alert['women_count']}")
        img = Image.open(BytesIO(requests.get(alert["image_url"]).content))
        st.image(img, width=400)
else:
    st.info("No alerts yet.")
