# qa_engine.py

import os
import json
import chromadb
from dotenv import load_dotenv
from neo4j import GraphDatabase
from openai import OpenAI
from sentence_transformers import SentenceTransformer

# --- Configuration and Initialization ---
load_dotenv()

# Initialize OpenAI Client
try:
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except Exception as e:
    print(f"Error initializing OpenAI client: {e}")
    exit()

class KnowledgeRetriever:
    """
    A class to retrieve context from both the vector and graph databases.
    """
    def __init__(self):
        print("Initializing Knowledge Retriever...")
        # Vector DB Connection
        self.vector_client = chromadb.PersistentClient(path="chroma_db")
        self.collection = self.vector_client.get_collection(name="github_knowledge_base")
        
        # Embedding Model
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Graph DB Connection
        uri = os.getenv("NEO4J_URI")
        neo4j_user = os.getenv("NEO4J_USER")
        neo4j_password = os.getenv("NEO4J_PASSWORD")
        
        # Validate environment variables
        if not uri:
            raise ValueError("NEO4J_URI environment variable is not set")
        if not neo4j_user or not neo4j_password:
            raise ValueError("NEO4J_USER and NEO4J_PASSWORD environment variables must be set")
            
        auth = (neo4j_user, neo4j_password)
        self.graph_driver = GraphDatabase.driver(uri, auth=auth)
        self.graph_driver.verify_connectivity()
        print("Retriever initialized successfully.")

    def _semantic_search(self, query_text, n_results=10):
        """Performs semantic search on ChromaDB."""
        print(f"\n1. Performing semantic search for: '{query_text}'")
        query_embedding = self.embedding_model.encode(query_text).tolist()
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        print(f"  - Found {len(results['ids'][0])} candidate nodes.")
        return results['ids'][0]

    def _graph_enrichment(self, node_ids):
        """Enriches candidate nodes with graph context from Neo4j."""
        print("\n2. Enriching candidates with graph context...")
        with self.graph_driver.session() as session:
            # <--- THIS IS THE CORRECTED AND FINAL QUERY --->
            result = session.run("""
            UNWIND $node_ids AS id
            MATCH (node {id: id})
            MATCH (author:User)-[:AUTHORED]->(pr:PullRequest)-[:INCLUDES*0..]->(node)
            
            WITH author, pr, node
            
            OPTIONAL MATCH (author)-[r:CONTRIBUTED_TO_TECHNOLOGY {in_pr: pr.id}]->(tech:Technology)
            
            WITH author, pr, node, COLLECT(DISTINCT tech.name) AS technologies, labels(node)[0] as node_type

            RETURN 
                author.id AS author,
                node_type,
                CASE node_type
                    WHEN 'PullRequest' THEN node.title
                    WHEN 'Commit' THEN node.message
                    ELSE 'N/A'
                END AS content,
                pr.url as pr_url,
                technologies
            """, node_ids=node_ids)
            
            context_list = [record.data() for record in result]
            print(f"  - Generated {len(context_list)} context snippets.")
            return context_list

    def retrieve_context(self, query_text):
        """The main retrieval method orchestrating the two-step process."""
        candidate_ids = self._semantic_search(query_text)
        if not candidate_ids:
            return ""
            
        enriched_context = self._graph_enrichment(candidate_ids)
        
        # Format the context into a single string for the LLM
        context_str = ""
        for item in enriched_context:
            context_str += (
                f"- User '{item['author']}' worked on a {item['node_type']} "
                f"with content: '{item['content']}'. "
                f"PR URL: {item['pr_url']}. "
                f"Involved technologies: {', '.join(item['technologies']) if item['technologies'] else 'N/A'}.\n"
            )
        return context_str

class AnswerSynthesizer:
    """
    Uses an LLM to synthesize an answer from the retrieved context.
    """
    def __init__(self, client):
        self.client = client
        self.model = "gpt-4o-mini" # You can use "gpt-4" for higher quality

    def generate_answer(self, query, context):
        print("\n3. Synthesizing answer with LLM...")
        if not context:
            return "I couldn't find any relevant information in the knowledge base to answer your question."

        # This is our prompt template. It's crucial for guiding the LLM.
        prompt = f"""
        You are an AI assistant designed to provide expertise profiles from a GitHub knowledge base.
        Your goal is to answer the user's question based *only* on the provided context.
        Do not make up information. If the context doesn't contain the answer, say so.
        Summarize the findings and identify the key people related to the user's query.
        For each person you identify, cite the evidence from the context.

        CONTEXT:
        ---
        {context}
        ---

        USER QUESTION: {query}

        ANSWER:
        """
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a helpful engineering knowledge assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2 # Lower temperature for more factual answers
        )
        print("  - LLM response received.")
        return response.choices[0].message.content


# --- Main Execution Block ---
# if __name__ == "__main__":
#     retriever = KnowledgeRetriever()
#     synthesizer = AnswerSynthesizer(openai_client)

#     # --- ASK YOUR QUESTION HERE ---
#     user_question = "Who are the experts working with Azure AI?"

#     print("-" * 50)
#     print(f"USER QUESTION: {user_question}")
#     print("-" * 50)

#     # 1. Retrieve Context
#     retrieved_context = retriever.retrieve_context(user_question)
    
#     # 2. Generate Answer
#     final_answer = synthesizer.generate_answer(user_question, retrieved_context)
    
#     print("\n" + "=" * 50)
#     print("FINAL ANSWER:")
#     print(final_answer)
#     print("=" * 50)