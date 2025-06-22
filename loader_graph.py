# loader_graph.py
import os
import json
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load environment variables
load_dotenv()
URI = os.getenv("NEO4J_URI")
AUTH = (os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))

def load_nodes(driver, nodes_data):
    """Loads nodes into Neo4j, using MERGE to avoid duplicates."""
    print(f"Loading {len(nodes_data)} nodes...")
    with driver.session() as session:
        # This query is now corrected with the required WITH clause.
        # It's also slightly optimized to use a single SET.
        result = session.run("""
        UNWIND $nodes AS node_data
        MERGE (n {id: node_data.id})
        SET n += node_data.properties
        WITH n, node_data
        CALL apoc.create.addLabels(n, [node_data.label]) YIELD node
        RETURN count(node)
        """, nodes=nodes_data)
        count = result.single()[0]
        print(f"Successfully merged {count} nodes.")

def load_edges(driver, edges_data):
    """Loads relationships (edges) into Neo4j."""
    print(f"Loading {len(edges_data)} edges...")
    with driver.session() as session:
        # This query is also updated to be more robust by using WITH.
        result = session.run("""
        UNWIND $edges AS edge_data
        MATCH (source {id: edge_data.source})
        MATCH (target {id: edge_data.target})
        WITH source, target, edge_data
        CALL apoc.create.relationship(
            source, 
            edge_data.relationship, 
            edge_data.properties, 
            target
        ) YIELD rel
        RETURN count(rel)
        """, edges=edges_data)
        count = result.single()[0]
        print(f"Successfully created {count} relationships.")

if __name__ == "__main__":
    try:
        with GraphDatabase.driver(URI, auth=AUTH) as driver:
            driver.verify_connectivity()
            print("Successfully connected to Neo4j.")

            # Optional: This clears the database for a fresh load. Good for testing.
            print("Clearing existing database...")
            with driver.session() as session:
                session.run("MATCH (n) DETACH DELETE n")

            with open("nodes.json", 'r', encoding='utf-8') as f:
                nodes = json.load(f)
            with open("edges.json", 'r', encoding='utf-8') as f:
                edges = json.load(f)
            
            load_nodes(driver, nodes)
            load_edges(driver, edges)
            print("\nGraph data loading complete!")
    except Exception as e:
        print(f"An error occurred: {e}")