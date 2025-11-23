import streamlit as st
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import *

st.set_page_config(page_title="Manage RSS Feeds", page_icon="📡")

init_session_state()

def load_feeds():
    data = make_api_request("GET", ENDPOINTS["rss_feeds"])
    if data:
        if isinstance(data, dict) and "feeds" in data:
            return data["feeds"]
        elif isinstance(data, list):
            return data
    return []

def discover_feeds(url):
    payload = {"url": url}
    headers = {"Content-Type": "application/json"}
    return make_api_request("POST", ENDPOINTS["discover_rss"], json=payload, headers=headers)

def add_feed(url):
    payload = {"url": url}
    headers = {"Content-Type": "application/json"}
    return make_api_request("POST", ENDPOINTS["add_rss"], json=payload, headers=headers)

def main():
    st.title("📡 Manage RSS Feeds")
    
    # Backend Status
    if not check_backend_status():
        st.error("🔴 Backend Offline - Please start the backend server")
        st.stop()
    
    # Tabs
    tab1, tab2 = st.tabs(["🔍 Discover & Add", "📋 Current Feeds"])
    
    with tab1:
        st.subheader("🔍 Discover RSS Feeds")
        
        url = st.text_input("Enter website URL:", placeholder="https://example.com")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔍 Discover Feeds", disabled=not url):
                if url:
                    with st.spinner("Discovering RSS feeds..."):
                        result = discover_feeds(url)
                        if result and "feeds" in result:
                            st.session_state.discovered_feeds = result["feeds"]
                        else:
                            st.error("No RSS feeds found or discovery failed")
        
        with col2:
            if st.button("➕ Add Direct URL", disabled=not url):
                if url:
                    with st.spinner("Adding RSS feed..."):
                        result = add_feed(url)
                        if result:
                            st.success("✅ Feed added successfully!")
                            st.rerun()
                        else:
                            st.error("❌ Failed to add feed")
        
        # Show discovered feeds
        if hasattr(st.session_state, 'discovered_feeds') and st.session_state.discovered_feeds:
            st.subheader("📡 Discovered Feeds")
            for feed in st.session_state.discovered_feeds:
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**{feed.get('title', 'Unknown Title')}**")
                        st.caption(feed.get('url', ''))
                        if feed.get('description'):
                            st.write(feed['description'][:100] + "...")
                    
                    with col2:
                        if st.button("➕ Add", key=f"add_{feed.get('url', '')}"):
                            with st.spinner("Adding feed..."):
                                result = add_feed(feed['url'])
                                if result:
                                    st.success("✅ Added!")
                                    st.rerun()
                    st.divider()
    
    with tab2:
        st.subheader("📋 Current RSS Feeds")
        
        feeds = load_feeds()
        
        if not feeds:
            st.info("No RSS feeds added yet. Use the 'Discover & Add' tab to add some!")
            return
        
        for feed in feeds:
            with st.container():
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"**{feed.get('title', 'Unknown Title')}**")
                    st.caption(f"🔗 {feed.get('url', '')}")
                    if feed.get('description'):
                        st.write(feed['description'])
                    st.caption(f"📅 Added: {feed.get('created_at', 'Unknown')}")
                
                with col2:
                    if st.button("🗑️", key=f"delete_{feed.get('id', '')}", help="Delete feed"):
                        # TODO: Implement delete functionality
                        st.warning("Delete functionality not implemented yet")
                
                st.divider()
        
        st.metric("Total Feeds", len(feeds))

if __name__ == "__main__":
    main()
