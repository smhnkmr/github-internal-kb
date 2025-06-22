# app.py

import streamlit as st
from qa_engine import KnowledgeRetriever, AnswerSynthesizer, openai_client # Import our backend

# --- Page Configuration ---
st.set_page_config(
    page_title="GitHub Expertise Finder",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 GitHub Expertise Finder")
st.write("Ask a question to find experts in your organization based on their GitHub contributions.")

# --- Caching the Backend ---
# @st.cache_resource is a key Streamlit command. It tells Streamlit to run this
# function only once, and then keep the returned object in cache. This prevents
# reloading the models and reconnecting to the databases on every user interaction.
@st.cache_resource
def get_retriever():
    return KnowledgeRetriever()

@st.cache_resource
def get_synthesizer():
    # Using the openai_client we imported from qa_engine
    return AnswerSynthesizer(openai_client)

retriever = get_retriever()
synthesizer = get_synthesizer()

# --- UI Elements ---
example_questions = [
    "Who are the experts on handling streaming data or responses?",
    "What work has been done related to speech recognition?",
    "Who knows about WebSockets or state management?",
    "Find me people who have worked with TailwindCSS.",
]

# Use session state to remember the selected question
if 'selected_question' not in st.session_state:
    st.session_state.selected_question = ""

# Display example questions as buttons
st.write("**Example Questions:**")
cols = st.columns(len(example_questions))
for i, question in enumerate(example_questions):
    if cols[i].button(question, use_container_width=True):
        st.session_state.selected_question = question

# The main text input for the user's question
user_question = st.text_input(
    "Ask a question or select an example above:", 
    key="main_question", 
    value=st.session_state.selected_question
)

if st.button("Get Answer"):
    if not user_question:
        st.warning("Please enter a question.")
    else:
        # This is where the magic happens
        with st.spinner("Step 1/2: Searching the knowledge base..."):
            retrieved_context = retriever.retrieve_context(user_question)

        with st.spinner("Step 2/2: Synthesizing the answer with AI..."):
            final_answer = synthesizer.generate_answer(user_question, retrieved_context)
        
        st.divider()
        st.subheader("Answer")
        st.markdown(final_answer)

        # A 'Show Context' expander to see what the LLM used for its answer
        with st.expander("Show Retrieved Context"):
            st.text(retrieved_context)