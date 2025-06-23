# intelligent_app.py

import streamlit as st
import os
import json
from dotenv import load_dotenv
from openai import OpenAI

# Import our refactored tool functions
from graph_analyzer import get_user_expertise, get_experts_for_technology
from qa_engine import semantic_search_for_concept

# --- Configuration ---
load_dotenv()
try:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except Exception as e:
    st.error(f"Failed to initialize OpenAI client: {e}")
    st.stop()

class OpenAIRouter:
    def __init__(self):
        # Map tool names to their actual Python functions
        self.available_tools = {
            "get_user_expertise": get_user_expertise,
            "get_experts_for_technology": get_experts_for_technology,
            "semantic_search_for_concept": semantic_search_for_concept,
        }
        self.model = "gpt-4o-mini" # A great, cost-effective model that supports tool calling

    def _get_tool_definitions(self):
        """
        Returns the JSON schema definitions for the tools the model can use.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_user_expertise",
                    "description": "Get a summary of a specific user's skills, expertise, and contributions.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_id": {
                                "type": "string",
                                "description": "The unique ID or login name of the user, e.g., 'mchill'",
                            },
                        },
                        "required": ["user_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_experts_for_technology",
                    "description": "Find a list of people experienced with a specific programming language, library, or technology.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "technology_name": {
                                "type": "string",
                                "description": "The name of the technology, e.g., 'TypeScript', 'React'",
                            },
                        },
                        "required": ["technology_name"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "semantic_search_for_concept",
                    "description": "Default tool for general, conceptual, or topic-based questions when a specific user or technology is not named.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query_text": {
                                "type": "string",
                                "description": "The user's original question or a summary of their query.",
                            },
                        },
                        "required": ["query_text"],
                    },
                },
            },
        ]

    def route(self, messages: list):
        st.info("**Thinking...** Analyzing your question to find the best tool.")
        
        # 1. First API Call (The "Planning" Step)
        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=self._get_tool_definitions(),
            tool_choice="auto",
        )
        response_message = response.choices[0].message
        
        # Convert ChatCompletionMessage to dictionary format for session state
        message_dict = {"role": response_message.role, "content": response_message.content}
        if response_message.tool_calls:
            message_dict["tool_calls"] = response_message.tool_calls
        messages.append(message_dict)
        
        # Check if the model wants to call a tool
        if response_message.tool_calls:
            tool_call = response_message.tool_calls[0]
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            st.success(f"**Router Decision:** Chose the `{function_name}` tool.")
            st.write("Arguments:", function_args)

            # 2. Execute the Chosen Tool
            function_to_call = self.available_tools[function_name]
            with st.spinner(f"Running tool `{function_name}`..."):
                function_response = function_to_call(**function_args)
            
            st.write("Tool Output:")
            st.info(function_response)

            # 3. Second API Call (The "Synthesis" Step)
            # Append the tool's output to the conversation history
            messages.append(
                {
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": function_response,
                }
            )
            
            with st.spinner("Synthesizing final answer..."):
                final_response = client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                )
            return final_response.choices[0].message.content or "I apologize, but I couldn't generate a response."
        else:
            # The model chose to answer directly
            st.warning("The AI chose to answer directly without using a specific tool.")
            return response_message.content or "I apologize, but I couldn't generate a response."

# --- Streamlit UI ---
st.set_page_config(page_title="Intelligent GitHub KB", layout="wide", page_icon="🧠")
st.title("🧠 Intelligent Knowledge Base Router (OpenAI)")
st.write("This app uses an LLM to automatically route your question to the best data source.")

# Use caching to only initialize the router once
@st.cache_resource
def get_router():
    return OpenAIRouter()

router = get_router()

st.write("**Example Questions:**")
st.markdown("""
- **User Expertise:** `What are the skills and expertise of user 'mchill'?`
- **Technology Experts:** `Who are the main contributors to React?`
- **Semantic Search:** `What work has been done on Azure AI?`
""")

# --- Main app logic ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": "You are a helpful engineering knowledge assistant."}]

for message in st.session_state.messages:
    # Don't display the system message or tool calls in the chat UI
    # Handle both dictionary messages and OpenAI message objects
    try:
        if isinstance(message, dict):  # Dictionary message
            role = message.get("role", "")
            content = message.get("content", "")
            has_tool_calls = "tool_calls" in message
        elif hasattr(message, 'role'):  # OpenAI message object
            role = getattr(message, 'role', '')
            content = getattr(message, 'content', '')
            has_tool_calls = hasattr(message, 'tool_calls') and getattr(message, 'tool_calls', None)
        else:
            continue  # Skip unknown message types
        
        if role in ["user", "assistant"] and not has_tool_calls and content:
            with st.chat_message(role):
                st.markdown(content)
    except (KeyError, TypeError, AttributeError):
        # Skip malformed messages
        continue

if prompt := st.chat_input("Ask a question..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        final_answer = router.route(st.session_state.messages)
        st.markdown(final_answer)
        # Append the final answer to history for context in the next turn
        st.session_state.messages.append({"role": "assistant", "content": final_answer})