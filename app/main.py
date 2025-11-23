import streamlit as st

# Set page config
st.set_page_config(
    page_title="RSS Chat Assistant",
    page_icon="🤖",
    layout="wide"
)

# Welcome page
st.title("🤖 RSS Chat Assistant")
st.markdown("### Welcome to your AI-powered RSS reader!")

st.info("👈 **Use the sidebar to navigate:**")
st.markdown("""
- **📊 Dashboard** - View and select RSS articles
- **📡 Manage Feeds** - Add and manage RSS feeds  
- **🤖 AI Chat** - Chat with AI about selected articles
""")

st.markdown("---")
st.markdown("**Get started by adding some RSS feeds, then explore articles and chat with AI!**")
