import streamlit as st
import uuid
import time

def initialize_conversation_state():
    """Initialize session state variables for conversation history."""
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.session_state.used_agents = []
        st.session_state.active_agent = None
        st.session_state.conversation_title = ""
        st.session_state.current_conversation_id = str(uuid.uuid4())
        st.session_state.conversation_history = {}

def save_conversation(conversation_id, title, messages):
    """Save the current conversation to history."""
    # Initialize conversation_history if it doesn't exist
    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = {}
        
    if not title:
        # Get first few words of first message as the title
        user_msg = next((m for m in messages if m["role"] == "user"), None)
        if user_msg:
            title = " ".join(user_msg["content"].split()[:5])
            if len(title) > 30:
                title = title[:27] + "..."
        else:
            title = "Untitled Chat"
            
    st.session_state.conversation_history[conversation_id] = {
        'title': title,
        'messages': messages.copy(),
        'timestamp': time.strftime("%Y-%m-%d %H:%M")
    }

def render_conversation_history_sidebar():
    """Render the conversation history in the sidebar."""
    # Add New Chat button at the top
    if st.button("📝 New Chat", key="new_chat_button", use_container_width=True):
        # Save current conversation if it has messages
        if st.session_state.messages:
            save_conversation(
                st.session_state.current_conversation_id,
                st.session_state.conversation_title or "Untitled Chat",
                st.session_state.messages
            )
        
        # Start a new conversation
        st.session_state.current_conversation_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.session_state.conversation_title = ""
        st.rerun()
    
    # Add a separator
    st.markdown("<hr style='margin: 20px 0;'>", unsafe_allow_html=True)
    
    # Display conversation history if available
    if st.session_state.conversation_history:
        st.markdown("<h3 style='color: #333333; margin-bottom: 15px;'>Conversation History</h3>", unsafe_allow_html=True)
        
        # Display most recent conversations first
        sorted_convs = sorted(
            st.session_state.conversation_history.items(), 
            key=lambda x: x[1]['timestamp'], 
            reverse=True
        )
        
        for i, (conv_id, conv_data) in enumerate(sorted_convs[:5]):  # Show up to 5 most recent conversations
            # Highlight current conversation
            is_current = conv_id == st.session_state.current_conversation_id
            
            with st.container():
                col_a, col_b = st.columns([4, 1])
                with col_a:
                    # Display title and timestamp with darker text
                    title = conv_data['title'] if conv_data['title'] else "Untitled Chat"
                    if is_current:
                        st.markdown(f"<div style='color: #000000; font-weight: bold;'>{title} <em>(Current)</em></div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div style='color: #333333;'>{title}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='color: #666666; font-size: 12px;'>{conv_data['timestamp']}</div>", unsafe_allow_html=True)
                
                with col_b:
                    # Show a button to load conversation if not the current one
                    if not is_current:
                        # Use the index to create a unique key
                        if st.button("Load", key=f"load_conv_{i}"):
                            # Save current conversation first if needed
                            if st.session_state.messages:
                                save_conversation(
                                    st.session_state.current_conversation_id,
                                    st.session_state.conversation_title or "Untitled Chat",
                                    st.session_state.messages
                                )
                            
                            # Load the selected conversation
                            st.session_state.current_conversation_id = conv_id
                            st.session_state.messages = conv_data['messages'].copy()
                            st.session_state.conversation_title = conv_data['title']
                            st.rerun()

# Demo app to show how to use this component
def main():
    st.set_page_config(page_title="Chat with Conversation History", layout="wide")
    
    # Initialize session state
    initialize_conversation_state()
    
    # Create a two-column layout
    col1, col2 = st.columns([1, 3])
    
    # Sidebar for conversation history
    with col1:
        # Add app header
        st.markdown("""
        <div style="display:flex;align-items:center;margin-bottom:20px;">
            <div style="font-size:24px;margin-right:10px;">💬</div>
            <div>
                <div style="font-size:20px;font-weight:bold;">Chat App</div>
                <div style="font-size:14px;color:#666;">With Conversation History</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Render conversation history
        render_conversation_history_sidebar()
    
    # Main chat area
    with col2:
        # Display chat messages
        for message in st.session_state.messages:
            if message["role"] == "user":
                st.chat_message("user").write(message["content"])
            else:
                st.chat_message("assistant").write(message["content"])
        
        # Chat input
        if prompt := st.chat_input("Type a message..."):
            # Add user message
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # Set conversation title from first message if not already set
            if not st.session_state.conversation_title and len(st.session_state.messages) == 1:
                title = " ".join(prompt.split()[:5])
                if len(title) > 30:
                    title = title[:27] + "..."
                st.session_state.conversation_title = title
            
            # Save conversation to history
            save_conversation(
                st.session_state.current_conversation_id,
                st.session_state.conversation_title,
                st.session_state.messages
            )
            
            # Show user message
            st.chat_message("user").write(prompt)
            
            # Simulate assistant response (replace with actual AI response)
            response = f"This is a response to: {prompt}"
            st.session_state.messages.append({"role": "assistant", "content": response})
            
            # Save updated conversation
            save_conversation(
                st.session_state.current_conversation_id,
                st.session_state.conversation_title,
                st.session_state.messages
            )
            
            # Show assistant message
            st.chat_message("assistant").write(response)
            
            # Rerun to update UI
            st.rerun()

if __name__ == "__main__":
    main()
