# loader_vectors.py
import json
import chromadb
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

# --- Configuration ---
MODEL_NAME = 'all-MiniLM-L6-v2' # A fast and effective open-source model
CHROMA_PATH = "chroma_db"       # Directory to store the Chroma database on disk
COLLECTION_NAME = "github_knowledge_base"

def generate_and_store_embeddings():
    """
    Loads nodes, generates embeddings for relevant text, and stores them in ChromaDB.
    """
    print("Initializing embedding model...")
    model = SentenceTransformer(MODEL_NAME)
    
    print("Initializing ChromaDB client...")
    # This creates a persistent client that saves data to the CHROMA_PATH directory.
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    
    # Get or create the collection. This is idempotent.
    collection = client.get_or_create_collection(name=COLLECTION_NAME)

    print("Loading nodes from nodes.json...")
    with open('nodes.json', 'r', encoding='utf-8') as f:
        nodes = json.load(f)

    # Filter for nodes that have meaningful text to embed
    nodes_to_embed = [
        node for node in nodes 
        if node.get('label') in ['PullRequest', 'Commit']
    ]
    print(f"Found {len(nodes_to_embed)} nodes to process for embeddings.")
    
    # Process in batches for efficiency
    batch_size = 100
    for i in tqdm(range(0, len(nodes_to_embed), batch_size), desc="Embedding & Storing in ChromaDB"):
        batch = nodes_to_embed[i:i+batch_size]
        
        ids_to_add = [node['id'] for node in batch]
        
        # Create a single "document" string for each item to represent its semantic meaning.
        documents_to_add = []
        for node in batch:
            if node['label'] == 'PullRequest':
                text = f"Title: {node['properties'].get('title', '')}. Body: {node['properties'].get('body', '')}"
            elif node['label'] == 'Commit':
                text = f"Commit message: {node['properties'].get('message', '')}"
            else:
                text = "" # Should not happen due to our filter
            documents_to_add.append(text)
        
        # Generate embeddings for the entire batch
        embeddings_to_add = model.encode(documents_to_add, show_progress_bar=False).tolist()
        
        # Add the data to ChromaDB
        collection.add(
            embeddings=embeddings_to_add,
            documents=documents_to_add,
            ids=ids_to_add
        )
    
    print(f"\nSuccessfully stored embeddings for {collection.count()} documents in collection '{COLLECTION_NAME}'.")

def test_semantic_search():
    """A quick test to show semantic search in action."""
    print("\n--- Testing Semantic Search ---")
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_collection(name=COLLECTION_NAME)
    query_text = "how to handle streaming responses"
    results = collection.query(query_texts=[query_text], n_results=3)
    
    print(f"Top 3 results for query: '{query_text}'")
    for doc_id in results['ids'][0]:
        print(f"  - ID: {doc_id}")

if __name__ == "__main__":
    generate_and_store_embeddings()
    test_semantic_search()