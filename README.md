Of course. Documenting the project is a critical final step. Here is a comprehensive summary suitable for a `README.md` file, covering the project's purpose, architecture, and a step-by-step guide to setting it up and running it.

---

# GitHub Expertise Knowledge Base

This project is an internal knowledge base that creates expertise profiles for an organization based on contributions to GitHub repositories. It uses a Retrieval-Augmented Generation (RAG) architecture with a hybrid knowledge base (Graph DB + Vector DB) to answer natural language questions about who knows what.

## Project Goal

The primary goal is to answer questions like:
*   "Who are the experts on our payment processing services?"
*   "What work has been done related to speech recognition?"
*   "Find me someone who has worked with both React and gRPC."
*   "Generate a summary of what Jane Doe worked on last quarter."

## Architecture

The system is built on a modern, scalable AI architecture:

1.  **Data Ingestion Pipeline:** Extracts data from the GitHub API.
2.  **Hybrid Knowledge Base:** Stores the processed data in two specialized databases.
    *   **Neo4j Graph Database:** Stores the explicit relationships between entities (Users, Repos, PRs, Commits, Files, Technologies). It answers "who, where, and how."
    *   **ChromaDB Vector Database:** Stores semantic vector embeddings of textual data (PR titles/bodies, commit messages). It answers "what is this about."
3.  **RAG Query Engine:** An application that orchestrates retrieval from both databases to provide rich, evidence-based context to an LLM.
4.  **Web UI:** A simple Streamlit application provides an interactive interface for users to ask questions.



---

## Project Phases & Setup Guide

This project is built in four distinct phases. Follow these steps to set up and run the entire system from scratch.

### Prerequisites

*   Python 3.8+
*   [Neo4j Desktop](https://neo4j.com/download/) installed and running.
*   API keys for:
    *   GitHub (Personal Access Token)
    *   An LLM provider (e.g., OpenAI or Google AI)

### Phase 1: Data Ingestion & Processing

**Goal:** Extract raw data from GitHub and transform it into a clean, structured graph format (`nodes.json` and `edges.json`).

**Steps:**
1.  **Clone the repository and install dependencies:**
    ```bash
    git clone <your-repo-url>
    cd <your-repo-name>
    pip install -r requirements.txt 
    ```
    *(You will need to create a `requirements.txt` file with all the libraries we installed).*

2.  **Configure Environment Variables:** Create a `.env` file in the root directory and populate it with your credentials:
    ```ini
    # .env
    GITHUB_TOKEN="ghp_YourGitHubToken..."
    NEO4J_URI="neo4j://localhost:7687"
    NEO4J_USER="neo4j"
    NEO4J_PASSWORD="your_neo4j_password"
    OPENAI_API_KEY="sk-YourOpenAIKey..." 
    # OR
    # GOOGLE_API_KEY="YourGoogleAIKey..."
    ```

3.  **Run the Extractor (`extractor.py`):**
    *   Modify the `TARGET_REPO_FULL_NAME` in `extractor.py` to point to your target repository.
    *   Execute the script to fetch raw data from GitHub. This will create `github_data.json`.
    ```bash
    python extractor.py
    ```

4.  **Run the Processor (`processor.py`):**
    *   This script reads `github_data.json` and transforms it.
    *   It creates `nodes.json` and `edges.json`, which represent the graph structure.
    ```bash
    python processor.py
    ```

### Phase 2: Knowledge Representation & Storage

**Goal:** Load the processed data into our live Neo4j and ChromaDB databases.

**Steps:**
1.  **Setup Neo4j:**
    *   In Neo4j Desktop, create a new local database instance.
    *   Set a password (and add it to your `.env` file).
    *   Go to the database **Settings (`...`) -> Plugins** and ensure the **APOC** plugin is installed.
    *   In the **Settings** pane, add the following line to enable APOC procedures, then save and restart the database:
      ```ini
      dbms.security.procedures.allowlist=apoc.create.*,apoc.coll.*
      ```

2.  **Load the Graph Database (`loader_graph.py`):**
    *   This script connects to your Neo4j instance and populates it with the nodes and edges.
    ```bash
    python loader_graph.py
    ```

3.  **Load the Vector Database (`loader_vectors.py`):**
    *   This script generates embeddings for PRs and Commits and stores them in a local ChromaDB instance.
    *   A `chroma_db/` directory will be created.
    ```bash
    python loader_vectors.py
    ```

### Phase 3: Retrieval and Synthesis

**Goal:** Implement the RAG engine that uses the knowledge base to answer questions.

**Steps:**
1.  **Refactor `qa_engine.py`:** Ensure the `if __name__ == "__main__"` block is removed from this file so it can be imported as a module by the UI.
2.  **Test the engine (Optional):** You can temporarily add the `__main__` block back to `qa_engine.py` and run it from the command line to test the retrieval and synthesis logic directly.
    ```bash
    # If testing directly
    python qa_engine.py
    ```

### Phase 4: Application & UI

**Goal:** Create a user-friendly web interface for the RAG system.

**Steps:**
1.  **Create the Streamlit App (`app.py`):** This file imports the `qa_engine` and builds the web interface.
2.  **Run the Application:**
    *   Execute the following command in your terminal.
    ```bash
    streamlit run app.py
    ```
    *   Your web browser will automatically open to the application, ready for you to ask questions.

---

### File Summary

*   `extractor.py`: Fetches data from GitHub API.
*   `processor.py`: Transforms raw data into a graph structure.
*   `loader_graph.py`: Loads the graph data into Neo4j.
*   `loader_vectors.py`: Creates and loads embeddings into ChromaDB.
*   `qa_engine.py`: Contains the core RAG logic (retrieval and synthesis classes).
*   `app.py`: The Streamlit web user interface.
*   `.env`: Stores all secrets and configuration.

This summary provides a clear and repeatable path for anyone to set up, understand, and use your powerful knowledge base project.