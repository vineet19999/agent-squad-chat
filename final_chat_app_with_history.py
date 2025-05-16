import streamlit as st
import openai
import time
import asyncio
import uuid
import duckduckgo_search as ddgs
from dotenv import load_dotenv
import os
import datetime
import json
import re
from typing import List, Dict

# Import our conversation history component
from conversation_history_component import initialize_conversation_state, save_conversation, render_conversation_history_sidebar

# Load environment variables from .env file
load_dotenv()

# Initialize the OpenAI client
openai.api_key = os.environ.get("OPENAI_API_KEY", "")

# Constants
MODEL = "gpt-4" # Upgraded to GPT-4 for more in-depth, thoughtful responses

# Simplified agent system
class Agent:
    def __init__(self, name, description, system_prompt, icon, color):
        self.name = name
        self.description = description
        self.system_prompt = system_prompt
        self.icon = icon
        self.color = color
        
    async def process(self, query, session_id, message_history=None):
        """Process a query using OpenAI with conversation history"""
        try:
            messages = [
                {"role": "system", "content": self.system_prompt}
            ]
            
            # Add conversation history
            if message_history:
                for msg in message_history[-10:]:
                    if msg["role"] in ["user", "assistant"]:
                        messages.append({
                            "role": msg["role"],
                            "content": msg["content"]
                        })
            
            # Add the current query and an additional system message to encourage depth
            messages.append({"role": "user", "content": query})
            
            # Add a final instruction to encourage depth
            messages.append({"role": "system", "content": "Please provide an in-depth, comprehensive response with specific details, examples, and thorough explanations. Aim for at least 400-600 words that thoroughly cover multiple aspects of the question."})
            
            response = openai.ChatCompletion.create(
                model=MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=3000,  # Increased token limit for longer, more detailed responses
                presence_penalty=0.1,
                frequency_penalty=0.1
            )
            
            # Clean and format the response text
            raw_response = response.choices[0].message.content
            clean_response = clean_response_text(raw_response)
            return clean_response
        except Exception as e:
            return f"Error: {str(e)}"

# Function to clean and fix formatting issues in AI responses
def clean_response_text(text):
    """Clean and fix common formatting issues in AI responses"""
    if not text:
        return text
        
    # Step 1: Replace problematic characters
    replacements = {
        '∗': '*',
        '′': "'",
        '´': "'",
        '–': '-',
        '—': '-',
        '−': '-'
    }
    
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    
    # Step 2: Fix Markdown formatting
    # Convert literal asterisks to HTML tags to prevent display issues
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', text)
    
    # Step 3: Fix spaces between run-together words
    # Add space between lowercase followed by uppercase (likely run-together words)
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    
    # Step 4: Fix broken words across lines
    # First, normalize newlines
    text = re.sub(r'\r\n|\r', '\n', text)
    
    # Then fix hyphenated words split across lines
    text = re.sub(r'(\w+)-\n(\w+)', r'\1\2', text)
    
    # Step 5: Remove excessive newlines (more than 2 in a row)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text

# Define agents with improved prompts
agents = [
    Agent(
        "Travel Agent",
        "Expert in travel planning and destinations",
        """You are a high-end travel agent with 20+ years of global travel experience. Your responses should be exceptionally comprehensive, providing the kind of detailed travel guidance that justifies professional consultation over simple internet searches.

When responding to travel inquiries, include:

1. For destinations:
   - In-depth cultural insights that only locals might know
   - Detailed month-by-month climate analysis with specific weather patterns
   - Off-the-beaten-path attractions with specific visiting hours and insider tips
   - Contextual history that enhances appreciation of landmarks

2. For itineraries:
   - Logistics with specific travel times between locations
   - Detailed daily schedules with timing and activity suggestions
   - Alternative plans for different weather conditions or unforeseen circumstances
   - Recommendations for local guides with specifics on what makes them exceptional

3. For accommodations:
   - Detailed pros and cons of each property
   - Specific room recommendations and room types to request
   - Insider tips about the property and surrounding area
   - Distance from major attractions and transportation hubs
""",
        "🧳",
        "#FF6B6B"
    ),
    Agent(
        "Tech Expert",
        "Software developer and tech specialist",
        """You are a senior software engineer and technical specialist with 15+ years of experience across multiple domains. Your responses should reflect deep expertise with comprehensive technical details that go well beyond surface-level explanations.

When answering technical questions, provide:

1. Conceptual Understanding:
   - Explain underlying principles and architectural considerations
   - Compare multiple approaches with detailed analysis of tradeoffs
   - Include both theoretical foundations and practical applications
   - Address scalability, maintainability, and reliability considerations

2. Code Solutions:
   - Provide comprehensive, production-ready code examples with:
     * Detailed comments explaining the reasoning behind each section
     * Error handling and edge case management
     * Performance optimization considerations
     * Best practices for readability and maintainability

3. Troubleshooting Guidance:
   - Suggest systematic debugging approaches with specific tool recommendations
   - Explain diagnostic techniques beyond the obvious first steps
   - Provide expected outputs or behavior at each troubleshooting stage
   - Include recovery strategies and preventative measures for the future
""",
        "💻",
        "#4ECDC4"
    ),
    Agent(
        "Health Advisor",
        "Expert in health, nutrition and fitness",
        """You are a team of specialized health educators with expertise in medicine, nutrition, fitness, and mental health. Your responses should be comprehensive, evidence-based, and holistic, addressing multiple dimensions of health and wellness.

When responding to health questions:

1. Essential Disclaimers and Context:
   - Begin with a clear disclaimer about not providing medical advice or diagnosis
   - Establish the importance of consulting healthcare professionals for personal health decisions

2. Comprehensive Explanations:
   - Provide detailed biological mechanisms in accessible language
   - Include multiple dimensions of health factors:
     * Related conditions and comorbidities
     * Demographic or individual factors that may influence outcomes
   - Explain how different body systems may be affected
   - Discuss interconnections between physical, mental, and emotional aspects
""",
        "🍎",
        "#FF9F1C"
    ),
    Agent(
        "General Assistant",
        "Knowledgeable all-purpose assistant",
        """You are a world-class intellectual guide with expertise spanning numerous fields of knowledge. Your responses should reflect intellectual depth, critical thinking, and a commitment to providing well-reasoned, comprehensive insights.

Incorporate the following elements in your responses:

1. Comprehensive Knowledge Framework:
   - Present multiple perspectives and schools of thought
   - Connect topics to broader themes and interdisciplinary relevance
   - Address both mainstream views and notable alternative perspectives

2. Intellectual Depth and Rigor:
   - Support claims with relevant evidence, examples, and reasoned analysis
   - Cite influential thinkers, researchers, or primary sources when relevant
   - Acknowledge complexity and nuance rather than oversimplifying
""",
        "🤖",
        "#9E9E9E"
    )
]

# Advanced routing based on query content
async def route_query(query, session_id, message_history):
    """Route to the best agent based on query analysis"""
    # Check if a specific agent is selected in session state
    if "active_agent" in st.session_state:
        for agent in agents:
            if agent.name == st.session_state.active_agent:
                response = await agent.process(query, session_id, message_history)
                return response, agent

    # Otherwise, select based on query content
    low_query = query.lower()
    
    # Check for travel related terms
    travel_keywords = ["travel", "trip", "vacation", "flight", "hotel", "destination", 
                       "tour", "visit", "country", "city", "beach", "mountain", "resort"]
    
    # Check for tech related terms
    tech_keywords = ["code", "program", "software", "computer", "app", "website", 
                     "developer", "error", "bug", "function", "database", "server",
                     "Python", "JavaScript", "HTML", "CSS", "API", "framework", "library"]
    
    # Check for health related terms
    health_keywords = ["health", "exercise", "diet", "nutrition", "workout", "fitness",
                       "medical", "doctor", "symptom", "food", "weight", "sleep", 
                       "medicine", "disease", "condition", "pain", "meal", "vitamin"]
    
    # Count matches in each category
    travel_count = sum(1 for word in travel_keywords if word in low_query)
    tech_count = sum(1 for word in tech_keywords if word in low_query)
    health_count = sum(1 for word in health_keywords if word in low_query)
    
    # Select the agent based on the highest keyword match count
    if travel_count > tech_count and travel_count > health_count:
        agent = agents[0]  # Travel Agent
    elif tech_count > travel_count and tech_count > health_count:
        agent = agents[1]  # Tech Expert
    elif health_count > travel_count and health_count > tech_count:
        agent = agents[2]  # Health Advisor
    else:
        agent = agents[3]  # General Assistant as default
    
    # Process the query with the selected agent
    response = await agent.process(query, session_id, message_history)
    return response, agent

def main():
    st.set_page_config(
        page_title="AI Agents Chat",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Add custom CSS
    st.markdown("""
    <style>
    /* General styling - lighter background */
    .stApp {
        background-color: #ffffff;
    }
    body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        background-color: #ffffff;
    }
    
    /* App header styling */
    .app-header {
        display: flex;
        align-items: center;
        margin-bottom: 20px;
        padding: 10px;
        border-radius: 10px;
        background: white;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    
    .app-title {
        font-size: 20px;
        font-weight: 600;
        color: #444;
    }
    
    .app-subtitle {
        font-size: 14px;
        color: #666;
    }
    
    /* Agent selection styling */
    .agent-panel {
        margin-bottom: 15px;
    }
    
    .agent-selection-title {
        font-size: 16px;
        font-weight: 600;
        margin-bottom: 10px;
        color: #444;
    }
    
    /* Chat message styling - improved visibility */
    .user-msg {
        background: #e6f2ff;
        padding: 12px 15px;
        border-radius: 18px;
        margin-bottom: 15px;
        position: relative;
        animation: fadeIn 0.3s ease-out;
        max-width: 85%;
        margin-left: auto;
        line-height: 1.5;
        color: #000000;
        z-index: 10;
    }
    
    .agent-msg {
        display: flex;
        margin-bottom: 15px;
        animation: fadeIn 0.3s ease-out;
        z-index: 10;
    }
    
    .agent-info {
        margin-right: 10px;
    }
    
    .message-content {
        background: #f5f5f5;
        padding: 12px 15px;
        border-radius: 18px;
        position: relative;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        max-width: 85%;
        line-height: 1.5;
        color: #000000;
        z-index: 10;
    }
    
    /* Input area styling - adjusted to not cover messages */
    .input-area {
        margin-top: 20px;
        padding: 15px;
        background: #f9f9f9;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
    }
    
    /* Section styling */
    .section-header {
        font-size: 16px;
        font-weight: 600;
        margin-top: 20px;
        margin-bottom: 10px;
        color: #444;
    }
    
    .section-divider {
        height: 1px;
        background: #e6e6e6;
        margin-bottom: 15px;
    }
    
    /* Animation */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    /* Hide streamlit elements */
    #MainMenu, footer {
        visibility: hidden;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize conversation history session state
    initialize_conversation_state()
    
    # Create a two-column layout
    col1, col2 = st.columns([1, 3])
    
    # Sidebar (col1) for agent selection and controls
    with col1:
        # Add app logo and title
        st.markdown("""
        <div class="app-header">
            <div style="margin-right: 15px; font-size: 28px;">🤖</div>
            <div>
                <div class="app-title">AI Agent Chat</div>
                <div class="app-subtitle">Powered by advanced AI agents</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Render conversation history sidebar
        render_conversation_history_sidebar()
        
        # Add a separator before agent selection
        st.markdown("<hr style='margin: 20px 0;'>", unsafe_allow_html=True)
        
        # Agent selection panel
        st.markdown("""
        <div class="agent-panel">
            <div class="agent-selection-title">Choose Your Agent</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Organize agents by category in columns
        col_a, col_b = st.columns(2)
        
        with col_a:
            # Create unique keys for agent selection buttons
            if st.button(f"{agents[0].icon} {agents[0].name}", key=f"select_agent_0", use_container_width=True):
                st.session_state.active_agent = agents[0].name
                if agents[0].name not in st.session_state.used_agents:
                    st.session_state.used_agents.insert(0, agents[0].name)
                st.rerun()
                
            if st.button(f"{agents[2].icon} {agents[2].name}", key=f"select_agent_2", use_container_width=True):
                st.session_state.active_agent = agents[2].name
                if agents[2].name not in st.session_state.used_agents:
                    st.session_state.used_agents.insert(0, agents[2].name)
                st.rerun()
            
        with col_b:
            # Create unique keys for agent selection buttons
            if st.button(f"{agents[1].icon} {agents[1].name}", key=f"select_agent_1", use_container_width=True):
                st.session_state.active_agent = agents[1].name
                if agents[1].name not in st.session_state.used_agents:
                    st.session_state.used_agents.insert(0, agents[1].name)
                st.rerun()
                
            if st.button(f"{agents[3].icon} {agents[3].name}", key=f"select_agent_3", use_container_width=True):
                st.session_state.active_agent = agents[3].name
                if agents[3].name not in st.session_state.used_agents:
                    st.session_state.used_agents.insert(0, agents[3].name)
                st.rerun()
                
        # Show recently used agents if any
        if st.session_state.used_agents:
            st.markdown("""
            <div class="agent-panel">
                <div class="agent-selection-title">Recent Agents</div>
            </div>
            """, unsafe_allow_html=True)
                
            # Show only unique agents, up to 3
            unique_agents = []
            for agent_name in st.session_state.used_agents:
                if agent_name not in unique_agents and len(unique_agents) < 3:
                    unique_agents.append(agent_name)
                
            # Create a grid of recent agents
            for agent_name in unique_agents:
                # Find agent object
                for agent in agents:
                    if agent.name == agent_name:
                        st.markdown(f"""
                        <div style='display:flex;align-items:center;background:white;padding:8px 12px;border-radius:8px;margin-bottom:8px;box-shadow:0 1px 3px rgba(0,0,0,0.05);'>
                            <div style='background:{agent.color};color:white;width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;margin-right:8px;'>{agent.icon}</div>
                            <div style='font-size:14px;font-weight:500;'>{agent.name}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        break
                
            # Controls panel
            st.markdown("""
            <div class="agent-panel">
                <div class="agent-selection-title">Controls</div>
            </div>
            """, unsafe_allow_html=True)
                
            # Reset button
            if st.button("🔄 Clear Conversation", use_container_width=True):
                st.session_state.messages = []
                if "active_agent" in st.session_state:
                    del st.session_state.active_agent
                st.rerun()
    
    # Main chat area (col2)
    with col2:
        # Show active agent if one is selected
        if "active_agent" in st.session_state:
            active_agent_name = st.session_state.active_agent
            for agent in agents:
                if agent.name == active_agent_name:
                    st.markdown(f"""
                    <div style='display:flex;align-items:center;background:white;padding:10px;border-radius:10px;margin-bottom:20px;box-shadow:0 2px 5px rgba(0,0,0,0.05);'>
                        <div style='background:{agent.color};color:white;width:40px;height:40px;border-radius:50%;display:flex;align-items:center;justify-content:center;margin-right:10px;font-size:20px;'>{agent.icon}</div>
                        <div>
                            <div style='font-weight:600;color:{agent.color};'>{agent.name}</div>
                            <div style='font-size:13px;color:#666;'>{agent.description}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    break
            
        # Display chat messages
        chat_container = st.container()
        with chat_container:
            # Space at top for padding
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            
            # Display all messages
            for message in st.session_state.messages:
                if message["role"] == "user":
                    st.markdown(f"<div class='user-msg'>{message['content']}</div>", unsafe_allow_html=True)
                else:
                    agent_name = message.get("agent_name", "Assistant")
                    # Find the agent to get its details
                    agent_icon = "💬"
                    agent_color = "#9E9E9E"
                    for agent in agents:
                        if agent.name == agent_name:
                            agent_icon = agent.icon
                            agent_color = agent.color
                            break
                    
                    # Add custom styling to message content before displaying
                    formatted_content = message["content"]
                    
                    # Apply minimal HTML formatting for readability without excessive spacing
                    # Format all-caps headers
                    formatted_content = re.sub(r'([A-Z]{5,})', r'<strong>\1</strong>', formatted_content)
                    
                    # Add reasonable spacing after headings
                    formatted_content = re.sub(r'(#+\s+[^\n]+)\n', r'\1<br>', formatted_content)
                    
                    # Replace newlines with single HTML breaks (not double)
                    formatted_content = formatted_content.replace('\n', '<br>')
                    
                    st.markdown(f"""
                    <div class='agent-msg'>
                        <div class='agent-info'>
                            <div style='background:{agent_color};color:white;width:30px;height:30px;border-radius:50%;display:flex;align-items:center;justify-content:center;'>{agent_icon}</div>
                        </div>
                        <div class='message-content'>{formatted_content}</div>
                    </div>
                    """, unsafe_allow_html=True)
            
            # Space at bottom for padding
            st.markdown("<div style='height: 100px;'></div>", unsafe_allow_html=True)
        
        # User input
        with st.container():
            st.markdown("<div class='input-area'>", unsafe_allow_html=True)
            # Input and send button
            col_input, col_button = st.columns([5, 1])
            with col_input:
                user_input = st.text_input("Message:", key="user_input", label_visibility="collapsed")
            with col_button:
                send_button = st.button("Send")
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Process user input
        if send_button and user_input:
            # Add user message to session state
            st.session_state.messages.append({"role": "user", "content": user_input})
            
            # Set conversation title from first user message if not already set
            if not st.session_state.conversation_title and len(st.session_state.messages) == 1:
                title = " ".join(user_input.split()[:5])
                if len(title) > 30:
                    title = title[:27] + "..."
                st.session_state.conversation_title = title
                
            # Save conversation to history after user message
            save_conversation(
                st.session_state.current_conversation_id,
                st.session_state.conversation_title or "Untitled Chat",
                st.session_state.messages
            )
            
            # Create typing indicator
            typing_placeholder = st.empty()
            
            # Determine which agent might respond based on keywords or active agent
            likely_agent = None
            if "active_agent" in st.session_state:
                for agent in agents:
                    if agent.name == st.session_state.active_agent:
                        likely_agent = agent
                        break
            
            if not likely_agent:
                # Guess based on keywords
                tech_keywords = ["code", "programming", "software", "computer", "developer", "python"]
                travel_keywords = ["travel", "vacation", "hotel", "flight", "destination", "tour"]
                health_keywords = ["health", "medical", "doctor", "sick", "pain", "fever"]
                
                if any(keyword in user_input.lower() for keyword in tech_keywords):
                    likely_agent = agents[1]  # Tech Expert
                elif any(keyword in user_input.lower() for keyword in travel_keywords):
                    likely_agent = agents[0]  # Travel Agent
                elif any(keyword in user_input.lower() for keyword in health_keywords):
                    likely_agent = agents[2]  # Health Advisor
                else:
                    likely_agent = agents[3]  # General Assistant
            
            # Show animated typing indicator
            agent_info_html = f"""
            <div class='agent-msg' style='width:120px;'>
                <div class='agent-info'>
                    <div style='background:{likely_agent.color};color:white;width:30px;height:30px;border-radius:50%;display:flex;align-items:center;justify-content:center;'>{likely_agent.icon}</div>
                </div>
                <div class="typing-animation">
                    <span class="dot"></span>
                    <span class="dot"></span>
                    <span class="dot"></span>
                </div>
            </div>
            """
            
            # Separate CSS to avoid percentage sign conflicts
            css_styling = """
            <style>
            .typing-animation {
                display: flex;
                align-items: center;
                column-gap: 5px;
                height: 20px;
            }
            .typing-animation .dot {
                display: block;
                width: 6px;
                height: 6px;
                border-radius: 50%;
                background-color: #606060;
                animation: typing-dot 1.5s infinite ease-in-out;
            }
            .typing-animation .dot:nth-child(1) { animation-delay: 0s; }
            .typing-animation .dot:nth-child(2) { animation-delay: 0.2s; }
            .typing-animation .dot:nth-child(3) { animation-delay: 0.4s; }
            @keyframes typing-dot {
                0%, 60%, 100% { transform: translateY(0); }
                30% { transform: translateY(-5px); }
            }
            </style>
            """
            
            # Combine HTML and CSS
            typing_placeholder.markdown(agent_info_html + css_styling, unsafe_allow_html=True)
            
            # Process message
            try:
                asyncio.set_event_loop(asyncio.new_event_loop())
                loop = asyncio.get_event_loop()
                response, agent = loop.run_until_complete(
                    route_query(user_input, st.session_state.session_id, st.session_state.messages)
                )
                loop.close()
                
                # Add agent to used agents list
                if agent.name not in st.session_state.used_agents:
                    st.session_state.used_agents.append(agent.name)
                
                # Save response to history
                st.session_state.messages.append({"role": "assistant", "content": response, "agent_name": agent.name})
                
                # Update conversation title if not set
                if not st.session_state.conversation_title and len(st.session_state.messages) >= 2:
                    user_first_msg = st.session_state.messages[0]["content"]
                    title = " ".join(user_first_msg.split()[:5])
                    if len(title) > 30:
                        title = title[:27] + "..."
                    st.session_state.conversation_title = title
                    
                # Save conversation to history
                save_conversation(
                    st.session_state.current_conversation_id,
                    st.session_state.conversation_title or "Untitled Chat", 
                    st.session_state.messages
                )
                
                # Clear typing indicator
                typing_placeholder.empty()
                
                # Rerun to update UI
                st.rerun()
                
            except Exception as e:
                # Handle error
                error_msg = f"Error: {str(e)}"
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg,
                    "agent_name": "System"
                })
                typing_placeholder.empty()
                st.rerun()

if __name__ == "__main__":
    main()
