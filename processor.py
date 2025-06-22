# processor.py

import json
import re
from pprint import pprint

# A dictionary of technologies and regex patterns to detect them in code diffs.
# This is a starting point - you can expand this extensively!
# The `r''` syntax denotes a raw string, which is good practice for regex patterns.
TECHNOLOGY_PATTERNS = {
    # JavaScript/TypeScript Frameworks & Libraries
    'React': r'import\s+.*\s+from\s+[\'"]react[\'"]',
    'Vue': r'import\s+.*\s+from\s+[\'"]vue[\'"]',
    'Svelte': r'import\s+.*\s+from\s+[\'"]svelte',
    'Angular': r'import\s+.*\s+from\s+[\'"]@angular/core[\'"]',
    'TailwindCSS': r'tailwindcss|@tailwind',
    'Vite': r'import\s+.*\s+from\s+[\'"]vite[\'"]',
    'Next.js': r'import\s+.*\s+from\s+[\'"]next/',
    'Express': r'require\([\'"]express[\'"]\)|import\s+.*\s+from\s+[\'"]express[\'"]',
    
    # Python Frameworks & Libraries
    'FastAPI': r'import\s+.*\s+from\s+[\'"]fastapi[\'"]',
    'Flask': r'import\s+.*\s+from\s+[\'"]flask[\'"]',
    'Django': r'import\s+.*\s+from\s+[\'"]django[\'"]',
    'Pandas': r'import\s+pandas\s+as',
    'NumPy': r'import\s+numpy\s+as',
    'PyTorch': r'import\s+torch',
    'TensorFlow': r'import\s+tensorflow\s+as',
    'LangChain': r'import\s+.*\s+from\s+[\'"]langchain',

    # Cloud & DevOps
    'Docker': r'FROM\s+|docker-compose.yml|Dockerfile',
    'GitHub Actions': r'on:\s+(push|pull_request)|jobs:', # Simplified for .yml files
    'Terraform': r'resource\s+[\'"]aws_', # Example for AWS provider
    'Kubernetes': r'apiVersion:\s+apps/v1|kind:\s+Deployment',

    # Database
    'SQLAlchemy': r'import\s+sqlalchemy',
    'Prisma': r'import\s+{\s*PrismaClient\s*}\s+from\s+[\'"]@prisma/client[\'"]',
    'PostgreSQL': r'postgresql:|psycopg2',
    'MongoDB': r'mongodb:|pymongo',
    
    # Other
    'GraphQL': r'import\s+.*\s+from\s+[\'"]graphql[\'"]|type\s+Query\s*{|type\s+Mutation\s*{',
}

def analyze_patch_for_tech(patch_text):
    """Analyzes a git patch for keywords to identify technologies."""
    if not patch_text:
        return set() # Return an empty set if patch is None
    
    found_tech = set()
    for tech, pattern in TECHNOLOGY_PATTERNS.items():
        if re.search(pattern, patch_text, re.IGNORECASE):
            found_tech.add(tech)
    return found_tech

def process_raw_data(filepath="github_data.json"):
    """
    Loads raw JSON data and processes it into a graph structure of nodes and edges.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: The file '{filepath}' was not found.")
        print("Please run 'extractor.py' first to generate the raw data.")
        return [], []

    nodes = []
    edges = []
    
    # Use dictionaries to keep track of created nodes to avoid duplicates.
    # The key will be a unique identifier (e.g., repo name, user login)
    seen_nodes = {
        "Repo": set(), "User": set(), "PullRequest": set(),
        "Commit": set(), "File": set(), "Technology": set()
    }

    for repo_data in data:
        # --- 1. Create Repository Node ---
        repo_id = repo_data['full_name']
        if repo_id not in seen_nodes["Repo"]:
            nodes.append({
                "id": repo_id, "label": "Repo",
                "properties": {
                    "name": repo_data['name'], "description": repo_data['description'],
                    "language": repo_data['language'], "url": repo_data['url']
                }
            })
            seen_nodes["Repo"].add(repo_id)

        # --- 2. Process Pull Requests ---
        for pr_data in repo_data['pull_requests']:
            pr_id = f"{repo_id}/pr/{pr_data['number']}"
            if pr_id not in seen_nodes["PullRequest"]:
                nodes.append({
                    "id": pr_id, "label": "PullRequest",
                    "properties": {
                        "title": pr_data['title'], "body": pr_data['body'],
                        "url": pr_data['url'], "created_at": pr_data['created_at'],
                        "merged_at": pr_data['merged_at']
                    }
                })
                seen_nodes["PullRequest"].add(pr_id)
            
            # --- 3. Process Users and their Relationships to PRs ---
            author_id = pr_data['author']
            if author_id and author_id not in seen_nodes["User"]:
                nodes.append({"id": author_id, "label": "User", "properties": {"login": author_id}})
                seen_nodes["User"].add(author_id)
            
            # Edge: User -> AUTHORED -> PullRequest
            if author_id:
                edges.append({"source": author_id, "target": pr_id, "relationship": "AUTHORED"})

            # --- 4. Process Commits ---
            for commit_data in pr_data['commits']:
                commit_id = commit_data['sha']
                if commit_id not in seen_nodes["Commit"]:
                    nodes.append({
                        "id": commit_id, "label": "Commit",
                        "properties": {
                            "message": commit_data['message'], "committed_at": commit_data['committed_at']
                        }
                    })
                    seen_nodes["Commit"].add(commit_id)
                
                # Edge: PullRequest -> INCLUDES -> Commit
                edges.append({"source": pr_id, "target": commit_id, "relationship": "INCLUDES"})

                # --- 5. Process Files and Technologies (Enrichment) ---
                for file_data in commit_data['files']:
                    # Create a unique ID for a file within a repo
                    file_id = f"{repo_id}/{file_data['filename']}"
                    if file_id not in seen_nodes["File"]:
                        nodes.append({"id": file_id, "label": "File", "properties": {"path": file_data['filename']}})
                        seen_nodes["File"].add(file_id)

                    # Edge: Commit -> MODIFIED -> File
                    edges.append({"source": commit_id, "target": file_id, "relationship": "MODIFIED"})

                    # Enrichment Step! Analyze the patch for technologies.
                    technologies = analyze_patch_for_tech(file_data.get('patch'))
                    for tech_name in technologies:
                        if tech_name not in seen_nodes["Technology"]:
                            nodes.append({"id": tech_name, "label": "Technology", "properties": {"name": tech_name}})
                            seen_nodes["Technology"].add(tech_name)
                        
                        # Edge: User -> CONTRIBUTED_TO_TECHNOLOGY -> Technology
                        # This creates a direct link from the user to the tech they touched.
                        # This is a powerful, high-level summary relationship.
                        if author_id:
                            edges.append({
                                "source": author_id, 
                                "target": tech_name, 
                                "relationship": "CONTRIBUTED_TO_TECHNOLOGY",
                                # We can add properties to edges too, providing context.
                                "properties": {"in_pr": pr_id, "in_commit": commit_id} 
                            })

    return nodes, edges

if __name__ == "__main__":
    print("Starting data processing from 'github_data.json'...")
    nodes, edges = process_raw_data("github_data.json")
    
    if not nodes and not edges:
        print("Processing aborted.")
    else:
        print("Processing complete.")
        print(f"Generated {len(nodes)} unique nodes.")
        print(f"Generated {len(edges)} total edges (relationships).")
        
        # Save the processed data to new files
        with open("nodes.json", "w", encoding='utf-8') as f:
            json.dump(nodes, f, ensure_ascii=False, indent=4)
            
        with open("edges.json", "w", encoding='utf-8') as f:
            json.dump(edges, f, ensure_ascii=False, indent=4)
            
        print("\nProcessed graph data saved to 'nodes.json' and 'edges.json'.")

        # Let's inspect a sample of the generated data to verify
        print("\n--- Sample Nodes ---")
        pprint(nodes[:3]) # First 3 nodes
        print("...")
        pprint(nodes[-3:]) # Last 3 nodes
        
        print("\n--- Sample Edges ---")
        pprint(edges[:3]) # First 3 edges
        print("...")
        pprint(edges[-3:]) # Last 3 edges