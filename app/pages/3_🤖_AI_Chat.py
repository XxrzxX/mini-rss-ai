import streamlit as st
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import *

st.set_page_config(page_title="AI Chat", page_icon="🤖")

init_session_state()

def create_chat_session(article_ids=None):
    payload = {
        "title": "New Chat",
        "article_ids": article_ids or []
    }
    headers = {"Content-Type": "application/json"}
    result = make_api_request("POST", f"{BASE_URL}/chat_sessions/", json=payload, headers=headers)
    return result.get("session_id") if result else None

def chat_with_session(session_id, message):
    payload = {"session_id": session_id, "message": message}
    headers = {"Content-Type": "application/json"}
    endpoint = f"{BASE_URL}/chat_sessions/{session_id}/chat"
    result = make_api_request("POST", endpoint, json=payload, headers=headers)
    return result.get("response") if result else None

def load_chat_sessions():
    """Load previous chat sessions"""
    result = make_api_request("GET", f"{BASE_URL}/chat_sessions/")
    return result.get("sessions", []) if result else []

def load_session_messages(session_id):
    """Load messages from a specific session"""
    # This would need a new backend endpoint to get session messages
    # For now, we'll just switch to the session
    return []

def main():
    st.title("🤖 AI Chat Assistant")
    
    # Backend Status
    if not check_backend_status():
        st.error("🔴 Backend Offline - Please start the backend server")
        st.stop()
    
    # Tabs for Chat and History
    tab1, tab2 = st.tabs(["💬 Current Chat", "📜 Chat History"])
    
    with tab2:
        st.subheader("📜 Previous Conversations")
        
        chat_sessions = load_chat_sessions()
        
        if chat_sessions:
            st.write(f"Found {len(chat_sessions)} previous chats:")
            
            # Display sessions in a nice format
            for session in chat_sessions[:10]:  # Show last 10
                session_id = session.get('id', '')
                title = session.get('title', 'Untitled Chat')
                created_at = session.get('created_at', '')
                article_count = len(session.get('article_ids', []))
                
                # Format date
                try:
                    from datetime import datetime
                    date_obj = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    date_str = date_obj.strftime("%B %d, %Y at %H:%M")
                except:
                    date_str = "Unknown date"
                
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**{title}**")
                        st.caption(f"📅 {date_str} • 📰 {article_count} articles")
                    
                    with col2:
                        if st.button("💬 Resume", key=f"resume_{session_id}"):
                            st.session_state.current_chat_session = session_id
                            st.session_state.chat_messages = []  # Will load from S3 in real implementation
                            st.session_state.selected_article_ids = session.get('article_ids', [])
                            st.success(f"✅ Resumed chat: {title}")
                            st.rerun()
                    
                    st.divider()
        else:
            st.info("No previous chats found. Start a new conversation!")
    
    with tab1:
        # Show context info
        if st.session_state.selected_article_ids:
            st.info(f"📰 Chatting with {len(st.session_state.selected_article_ids)} selected articles")
            if st.button("🗑️ Clear Article Context"):
                st.session_state.selected_article_ids = []
                st.session_state.current_chat_session = None
                st.rerun()
        else:
            st.info("💬 General chat mode - Select articles from Dashboard for specific context")
        
        # Chat controls
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Clear Chat"):
                st.session_state.chat_messages = []
                st.rerun()
        with col2:
            if st.button("🔄 New Session"):
                st.session_state.current_chat_session = None
                st.session_state.chat_messages = []
                st.rerun()
        
        # Show current session info
        if st.session_state.current_chat_session:
            st.caption(f"🔗 Session: {st.session_state.current_chat_session[:8]}...")
        
        # Create session if needed
        if not st.session_state.current_chat_session:
            with st.spinner("Creating chat session..."):
                session_id = create_chat_session(st.session_state.selected_article_ids)
                if session_id:
                    st.session_state.current_chat_session = session_id
                else:
                    st.error("❌ Failed to create chat session")
                    st.stop()
        
        # Display chat messages
        for message in st.session_state.chat_messages:
            if message["role"] == "user":
                st.chat_message("user").write(message["content"])
            else:
                st.chat_message("assistant").write(message["content"])

# Chat input MUST be outside tabs/columns/sidebar - NO INDENTATION
if prompt := st.chat_input("Ask me anything about the news..."):
    # Add user message
    st.session_state.chat_messages.append({"role": "user", "content": prompt})
    
    # Get AI response
    with st.spinner("AI is thinking..."):
        response = chat_with_session(st.session_state.current_chat_session, prompt)
        if response:
            st.session_state.chat_messages.append({"role": "assistant", "content": response})
        else:
            error_msg = "Sorry, I couldn't process your request. Please try again."
            st.session_state.chat_messages.append({"role": "assistant", "content": error_msg})
    
    # Rerun to show new messages
    st.rerun()

if __name__ == "__main__":
    main()
