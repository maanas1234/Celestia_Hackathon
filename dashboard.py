# dashboard.py
import streamlit as st
import requests
from PIL import Image
from io import BytesIO

# ------------------ CONFIG ------------------
BACKEND_URL = "http://127.0.0.1:8000"
st.set_page_config(page_title="Women Safety Admin", layout="wide")

# ------------------ SESSION STATE ------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "users" not in st.session_state:
    st.session_state.users = {}  # store username:password
if "username" not in st.session_state:
    st.session_state.username = ""

# ------------------ HELPER FUNCTIONS ------------------
def login_user(username, password):
    users = st.session_state.users
    if username in users and users[username] == password:
        st.session_state.logged_in = True
        st.session_state.username = username
        st.session_state.refresh = True
        st.stop()
    else:
        st.error("Incorrect username or password")

def signup_user(username, password):
    if username in st.session_state.users:
        st.error("Username already exists")
    else:
        st.session_state.users[username] = password
        st.success("Signup successful! Please login.")
        st.session_state.refresh = True
        st.stop()

# ------------------ HANDLE RERUN ------------------
if "refresh" in st.session_state and st.session_state.refresh:
    st.session_state.refresh = False
    st.experimental_rerun = lambda: st.stop()

# ------------------ LOGIN/SIGNUP PAGE ------------------
if not st.session_state.logged_in:
    st.title("🚨 Women Safety Admin Login")
    st.write("Please login or signup to access the dashboard")
    
    tab = st.radio("Choose:", ["Login", "Signup"], horizontal=True)
    
    with st.form("auth_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Submit")
        
        if submitted:
            if tab == "Login":
                login_user(username, password)
            else:
                signup_user(username, password)
    st.stop()

# ------------------ DASHBOARD PAGE ------------------
# Sidebar Logout
with st.sidebar:
    st.markdown(f"**Logged in as:** {st.session_state.username}")
    if st.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.refresh = True
        st.stop()

# Main dashboard UI
st.markdown("<h1 style='text-align:center;color:#FF3333;'>🚨 Women Safety Admin Dashboard (Model ε)</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;color:#555;'>Latest alerts from camera backend</p>", unsafe_allow_html=True)
st.markdown("---")

# Refresh button
# Refresh button
if st.button("🔄 Refresh Alerts"):
    # Clear cached session data so alerts are fetched again
    if "refresh_count" not in st.session_state:
        st.session_state.refresh_count = 0
    st.session_state.refresh_count += 1
    st.experimental_rerun()


# Fetch latest alerts
try:
    response = requests.get(f"{BACKEND_URL}/alerts/latest?limit=20", timeout=3)
    if response.status_code != 200:
        st.error(f"Backend returned {response.status_code}")
        data = []
    else:
        data = response.json()
except Exception as e:
    st.error("Cannot fetch alerts. Check backend URL.")
    st.write("Error:", e)
    data = []

# Display alerts
if data:
    for alert in data:
        st.markdown("---")
        st.subheader(alert.get("alert_text", "Alert"))
        st.text(f"Time: {alert.get('timestamp','-')} | Men: {alert.get('men_count',0)} | Women: {alert.get('women_count',0)}")
        img_url = alert.get("image_url")
        if img_url:
            try:
                img_resp = requests.get(img_url, timeout=3)
                img = Image.open(BytesIO(img_resp.content))
                st.image(img, width=480)
            except Exception as e:
                st.write("Could not load image:", e)
else:
    st.info("No alerts yet.")
