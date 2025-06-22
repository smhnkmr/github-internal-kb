import chromadb
from pprint import pprint

# --- Configuration ---
CHROMA_PATH = "chroma_db"
COLLECTION_NAME = "github_knowledge_base"

def explore_vector_db():
    print("Connecting to ChromaDB...")
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_collection(name=COLLECTION_NAME)

    # 1. Get the total number of items
    total_items = collection.count()
    print(f"\nCollection '{COLLECTION_NAME}' contains {total_items} items.")

    # 2. Get a specific item by its ID
    # Let's pick an ID we might have seen in Neo4j or qa_engine output
    sample_id = "OvidijusParsiunas/deep-chat/pr/190"
    print(f"\n--- Getting data for a specific ID: {sample_id} ---")
    item = collection.get(ids=[sample_id])
    pprint(item)

    # 3. Perform a semantic search
    print("\n--- Performing a semantic search ---")
    query = "web components and custom elements"
    print(f"Query: '{query}'")

    results = collection.query(
        query_texts=[query],
        n_results=10 # Ask for the top 3 most similar results
    )

    print("\nTop 3 semantic search results:")
    for i, doc_id in enumerate(results['ids'][0]):
        distance = results['distances'][0][i]
        document = results['documents'][0][i]
        
        print(f"\n{i+1}. ID: {doc_id}")
        print(f"   Distance: {distance:.4f} (lower is more similar)")
        print(f"   Document Text: '{document[:200]}...'")


if __name__ == "__main__":
    explore_vector_db()