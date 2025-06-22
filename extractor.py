# extractor.py

import os
import time
import json
from dotenv import load_dotenv
from github import Github, RateLimitExceededException, UnknownObjectException
from pprint import pprint

# --- Configuration ---
# Load environment variables from .env file
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") # Using a token is still recommended for higher rate limits

# --- IMPORTANT: Change this to the public repository you want to analyze ---
TARGET_REPO_FULL_NAME = "OvidijusParsiunas/deep-chat"

# Set a limit for the number of PRs to fetch for testing purposes.
# Set to None to fetch all. Be aware this can take a long time for large repos.
MAX_PRS_TO_FETCH = 25 

if not GITHUB_TOKEN:
    print("Warning: GitHub token not found. Running with lower API rate limits.")
# --- Authentication ---
# Even for public repos, authenticating gives you a much higher rate limit (5000 req/hr vs 60)
g = Github(GITHUB_TOKEN)
print(f"Successfully authenticated with GitHub.")


# --- Helper function for rate limiting ---
def wait_for_rate_limit_reset(github_instance):
    """Waits for the GitHub API rate limit to reset."""
    core_rate_limit = github_instance.get_rate_limit().core
    reset_seconds = (core_rate_limit.reset - datetime.datetime.utcnow()).total_seconds()
    sleep_time = max(0, reset_seconds) + 5  # Add 5 seconds buffer
    print(f"Rate limit exceeded. Waiting for {sleep_time:.2f} seconds...")
    time.sleep(sleep_time)

# --- Data Extraction Functions (Modified for a single repo) ---

def get_target_repo(github_instance, repo_full_name):
    """Fetches a single repository object by its full name."""
    print(f"\nFetching repository: {repo_full_name}")
    try:
        repo = github_instance.get_repo(repo_full_name)
        print(f"Successfully found repository: {repo.full_name}")
        return repo
    except UnknownObjectException:
        print(f"Error: Repository '{repo_full_name}' not found. Please check the name.")
        return None
    except RateLimitExceededException:
        wait_for_rate_limit_reset(github_instance)
        return get_target_repo(github_instance, repo_full_name) # Retry
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

def extract_pull_requests(repo, max_prs):
    """Extracts detailed information from closed pull requests in a repository."""
    print(f"\nExtracting Pull Requests for repo: {repo.name}")
    pr_data = []
    # We get 'closed' PRs because they represent completed work.
    pull_requests = repo.get_pulls(state='closed', sort='updated', direction='desc')

    # Use the max_prs limit if it's set
    pr_iterator = pull_requests[:max_prs] if max_prs is not None else pull_requests
    
    for pr in pr_iterator:
        if not pr.merged:
            continue
            
        print(f"  - Processing PR #{pr.number}: {pr.title}")
        try:
            # 1. Basic PR Info
            pr_info = {
                "id": pr.id, "number": pr.number, "title": pr.title, "body": pr.body,
                "state": pr.state, "url": pr.html_url, "created_at": pr.created_at.isoformat(),
                "merged_at": pr.merged_at.isoformat() if pr.merged_at else None,
                "author": pr.user.login if pr.user else "N/A",
                "reviewers": [r.login for r in pr.requested_reviewers],
            }

            # 2. Extract Comments
            pr_info["comments"] = [{
                "author": c.user.login if c.user else "N/A", "body": c.body, "created_at": c.created_at.isoformat()
            } for c in pr.get_issue_comments()]
            
            # 3. Extract Commits and File Diffs
            pr_info["commits"] = []
            for commit in pr.get_commits():
                files_changed = [{
                    "filename": f.filename, "status": f.status, "additions": f.additions,
                    "deletions": f.deletions, "patch": f.patch # The actual code diff
                } for f in commit.files]

                pr_info["commits"].append({
                    "sha": commit.sha,
                    "author": commit.commit.author.name if commit.commit.author else "N/A",
                    "email": commit.commit.author.email if commit.commit.author else "N/A",
                    "message": commit.commit.message,
                    "committed_at": commit.commit.author.date.isoformat(),
                    "files": files_changed
                })
            
            pr_data.append(pr_info)
        
        except RateLimitExceededException:
            wait_for_rate_limit_reset(g)
            print(f"  - Retrying PR #{pr.number} after rate limit wait.")
            # Simple retry logic here, more robust would be needed for a production system
            continue
        except Exception as e:
            print(f"  - Could not fully process PR #{pr.number}. Error: {e}")

    return pr_data

# --- Main Execution Logic ---
if __name__ == "__main__":
    repo = get_target_repo(g, TARGET_REPO_FULL_NAME)
    
    if repo:
        repo_info = {
            "name": repo.name, "full_name": repo.full_name, "description": repo.description,
            "language": repo.language, "topics": repo.get_topics(), "url": repo.html_url,
        }
        
        # Get PR data and add it to our repo info
        repo_info["pull_requests"] = extract_pull_requests(repo, MAX_PRS_TO_FETCH)
        
        # We wrap the single repo_info in a list to maintain the same data structure as before
        knowledge_base_data = [repo_info]

        print("\n\n--- EXTRACTION COMPLETE ---")
        print(f"Extracted {len(repo_info['pull_requests'])} PRs from '{repo.full_name}'.")
        
        output_filename = "github_data.json"
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(knowledge_base_data, f, ensure_ascii=False, indent=4)
            
        print(f"Raw data saved to {output_filename}")
        
        # Optional: Print a snippet of the data
        if knowledge_base_data and knowledge_base_data[0]["pull_requests"]:
            print("\n--- Sample of extracted data (first PR) ---")
            pprint(knowledge_base_data[0]["pull_requests"][0])
        else:
            print("No merged pull requests found or extracted.")