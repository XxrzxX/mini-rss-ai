import streamlit as st
import requests
from datetime import datetime
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import *

st.set_page_config(
    page_title="RSS Dashboard",
    page_icon="📊",
    layout="wide"
)

init_session_state()

def load_feeds():
    data = make_api_request("GET", ENDPOINTS["rss_feeds"])
    if data:
        if isinstance(data, dict) and "feeds" in data:
            return data["feeds"]
        elif isinstance(data, list):
            return data
    return []

def load_articles(limit=50):
    params = {"limit": limit}
    data = make_api_request("GET", ENDPOINTS["articles"], params=params)
    if data:
        if isinstance(data, dict) and "articles" in data:
            return data["articles"]
        elif isinstance(data, list):
            return data
    return []

def main():
    st.title("📊 RSS Dashboard")
    
    # Backend Status
    backend_online = check_backend_status()
    if backend_online:
        st.success("🟢 Backend Online")
    else:
        st.error("🔴 Backend Offline - Please start the backend server")
        st.stop()
    
    # Load data
    with st.spinner("Loading feeds and articles..."):
        feeds = load_feeds()
        articles = load_articles()
    
    # Stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📡 RSS Feeds", len(feeds))
    with col2:
        st.metric("📰 Articles", len(articles))
    with col3:
        st.metric("🤖 Selected for Chat", len(st.session_state.selected_article_ids))
    with col4:
        if st.button("🗑️ Clear Selection"):
            st.session_state.selected_article_ids = []
            st.rerun()
    
    # Articles Section
    st.subheader("📰 Recent Articles")
    
    if not articles:
        st.info("No articles found. Add some RSS feeds first!")
        st.info("👈 Use the sidebar to navigate to 'Manage Feeds'")
        return
    
    # Article selection and display
    for article in articles[:20]:  # Show first 20
        with st.container():
            col1, col2 = st.columns([1, 8])
            
            with col1:
                article_id = article.get('id', '')
                is_selected = article_id in st.session_state.selected_article_ids
                
                # Use unique key for each checkbox
                checkbox_key = f"select_{article_id}"
                selected = st.checkbox("", value=is_selected, key=checkbox_key)
                
                # Update selection state
                if selected and article_id not in st.session_state.selected_article_ids:
                    st.session_state.selected_article_ids.append(article_id)
                elif not selected and article_id in st.session_state.selected_article_ids:
                    st.session_state.selected_article_ids.remove(article_id)
            
            with col2:
                st.markdown(f"**{article.get('title', 'No Title')}**")
                st.caption(f"📡 {article.get('feed_title', 'Unknown Feed')} • {article.get('published_date', 'No Date')}")
                
                if article.get('summary'):
                    st.write(article['summary'][:200] + "..." if len(article.get('summary', '')) > 200 else article.get('summary', ''))
                
                if article.get('url'):
                    st.markdown(f"[🔗 Read Full Article]({article['url']})")
        
        st.divider()
    
    # Chat Action
    if st.session_state.selected_article_ids:
        st.success(f"✅ {len(st.session_state.selected_article_ids)} articles selected for AI chat")
        st.info("👈 Use the sidebar to navigate to 'AI Chat' to discuss selected articles")

if __name__ == "__main__":
    main()
