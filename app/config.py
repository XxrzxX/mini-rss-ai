import os
import streamlit as st
import requests
from contextlib import contextmanager

# Backend Configuration
BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# API Endpoints
ENDPOINTS = {
    "health": f"{BASE_URL}/health",
    "rss_feeds": f"{BASE_URL}/rss_feeds",
    "discover_rss": f"{BASE_URL}/discover_rss/",
    "add_rss": f"{BASE_URL}/add_rss/",
    "articles": f"{BASE_URL}/articles",
    "chat_sessions": f"{BASE_URL}/chat_sessions/",
}

# Session State Initialization
def init_session_state():
    defaults = {
        "feeds": [],
        "articles": [],
        "selected_article_ids": [],
        "current_chat_session": None,
        "chat_messages": [],
        "backend_status": "unknown",
        "loading": False,
        "error_message": None
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# Backend Status Check
@st.cache_data(ttl=30)
def check_backend_status():
    try:
        response = requests.get(ENDPOINTS["health"], timeout=5)
        return response.status_code == 200
    except:
        return False

# Error Handling
@contextmanager
def handle_api_errors():
    try:
        yield
    except requests.exceptions.ConnectionError:
        st.error("🔌 Backend not available. Please start the backend server.")
    except requests.exceptions.Timeout:
        st.error("⏱️ Request timed out. Please try again.")
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")

# API Request Helper
def make_api_request(method, endpoint, **kwargs):
    with handle_api_errors():
        if method.upper() == "GET":
            response = requests.get(endpoint, timeout=30, **kwargs)
        elif method.upper() == "POST":
            response = requests.post(endpoint, timeout=30, **kwargs)
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return None
