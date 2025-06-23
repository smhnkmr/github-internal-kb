# graph_analyzer.py

import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
from openai import OpenAI

# --- Configuration and Initialization ---
load_dotenv()

# Initialize OpenAI Client (can be swapped for Gemini)
try:
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except Exception as e:
    print(f"Error initializing OpenAI client: {e}")
    exit()

class GraphAnalyzer:
    """
    A class to answer structured questions starting from the Neo4j graph.
    """
    def __init__(self):
        print("Initializing Graph Analyzer...")
        # Graph DB Connection
        uri = os.getenv("NEO4J_URI")
        auth = (os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
        self.graph_driver = GraphDatabase.driver(uri, auth=auth)
        self.graph_driver.verify_connectivity()
        print("Graph Analyzer initialized successfully.")

    def _synthesize_answer(self, prompt, context):
        """A helper function to call the LLM for synthesis."""
        if not context:
            return "I could not find any data in the knowledge base for this query."
            
        full_prompt = f"""
        You are an expert engineering analyst. Based *only* on the provided context below, answer the user's question in a clear, concise summary.

        CONTEXT:
        ---
        {context}
        ---

        QUESTION: {prompt}

        ANSWER:
        """
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful engineering knowledge assistant."},
                {"role": "user", "content": full_prompt}
            ],
            temperature=0.2
        )
        return response.choices[0].message.content

    # --- Query Type 1: User Expertise ---
    def get_user_expertise(self, user_id):
        """
        Finds and summarizes the expertise of a specific user.
        """
        print(f"\n1. Analyzing expertise for user: '{user_id}'")
        question = f"What expertise does user '{user_id}' have?"
        
        with self.graph_driver.session() as session:
            # This query gets two things:
            # 1. A ranked list of technologies the user contributed to.
            # 2. A sample of their recent commit messages for more narrative context.
            result = session.run("""
            MATCH (u:User {id: $user_id})
            
            // Get ranked technology contributions
            CALL {
                WITH u
                MATCH (u)-[r:CONTRIBUTED_TO_TECHNOLOGY]->(t:Technology)
                RETURN t.name AS technology, count(r) AS contribution_count
                ORDER BY contribution_count DESC
            }
            
            // Get recent commit messages
            CALL {
                WITH u
                MATCH (u)-[:AUTHORED]->(:PullRequest)-[:INCLUDES]->(c:Commit)
                RETURN COLLECT(c.message)[..10] AS recent_commits // Get up to 10 recent messages
            }
            
            RETURN technology, contribution_count, recent_commits
            """, user_id=user_id)
            
            # Format the context for the LLM
            context_str = ""
            records = [record.data() for record in result]
            if not records:
                return "No data found for this user."
            
            context_str += "Ranked Technology Contributions:\n"
            for record in records:
                if record['technology']:
                    context_str += f"- {record['technology']}: {record['contribution_count']} contributions\n"

            # Add commit messages (they will be duplicated, so we just take the first list)
            if records[0]['recent_commits']:
                context_str += "\nSample of recent commit messages:\n"
                for msg in records[0]['recent_commits']:
                    context_str += f"- {msg.strip()}\n"

        print("  - Context retrieved from graph. Synthesizing answer...")
        return self._synthesize_answer(question, context_str)

    # --- Query Type 2: Technology Experts ---
    def get_experts_for_technology(self, technology_name):
        """
        Finds all users who have expertise in a given technology, ranked by contribution.
        """
        print(f"\n2. Finding experts for technology: '{technology_name}'")
        question = f"Who are all the users who have expertise in technology '{technology_name}'?"

        with self.graph_driver.session() as session:
            # This query finds all users connected to a technology and ranks them.
            result = session.run("""
            MATCH (u:User)-[r:CONTRIBUTED_TO_TECHNOLOGY]->(t:Technology {name: $tech_name})
            RETURN u.id as user, count(r) as contribution_count
            ORDER BY contribution_count DESC
            LIMIT 10 // Limit to the top 10 experts
            """, tech_name=technology_name)

            # Format the context for the LLM
            context_str = f"List of users who contributed to {technology_name}, ranked by number of contributions:\n"
            records = [record.data() for record in result]
            if not records:
                return f"No users found with contributions to '{technology_name}'."
            
            for record in records:
                context_str += f"- User: {record['user']}, Contributions: {record['contribution_count']}\n"
        
        print("  - Context retrieved from graph. Synthesizing answer...")
        return self._synthesize_answer(question, context_str)



# graph_analyzer.py (Refactored for Router)
# ... (all imports and class definitions remain the same) ...

# NEW: Top-level functions for the router to call
def get_user_expertise(user_id: str):
    """
    Finds and summarizes the expertise of a specific user.
    """
    analyzer = GraphAnalyzer()
    return analyzer.get_user_expertise(user_id)

def get_experts_for_technology(technology_name: str):
    """
    Finds all users who have expertise in a given technology.
    """
    analyzer = GraphAnalyzer()
    return analyzer.get_experts_for_technology(technology_name)

# The rest of the file (class definitions) stays the same.
# Make sure the old `if __name__ == "__main__"` block is removed.


# --- Main Execution Block ---
# if __name__ == "__main__":
#     analyzer = GraphAnalyzer()

#     # --- Question 1: What expertise does a user have? ---
#     user_expertise_answer = analyzer.get_user_expertise(user_id="dvartic")
    
#     print("\n" + "=" * 50)
#     print("QUESTION: What expertise does user 'dvartic' have?")
#     print("-" * 20)
#     print("FINAL ANSWER:")
#     print(user_expertise_answer)
#     print("=" * 50)


#     # --- Question 2: Who are the experts for a technology? ---
#     # Try 'TypeScript', 'React', 'Svelte' etc.
#     tech_experts_answer = analyzer.get_experts_for_technology(technology_name="React")
    
#     print("\n" + "=" * 50)
#     print("QUESTION: Who are all the users who has expertise in technology 'React'?")
#     print("-" * 20)
#     print("FINAL ANSWER:")
#     print(tech_experts_answer)
#     print("=" * 50)