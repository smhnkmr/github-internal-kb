import os
from dotenv import load_dotenv
from github import Github

# Load environment variables from .env file
load_dotenv()

# Get the token from the environment variable
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

if not GITHUB_TOKEN:
    raise ValueError("GitHub token not found. Please set it in the .env file.")

# --- Authentication ---
# Using a personal access token
try:
    g = Github(GITHUB_TOKEN)

    # Get the authenticated user
    user = g.get_user()
    print(f"Successfully authenticated as: {user.login}")
    print("-" * 20)
    
    # Example: List first 5 repositories the user has access to
    print("First 5 repositories you can access:")
    for repo in g.get_repos()[:25]:
        print(f"- {repo.full_name}")

except Exception as e:
    print(f"An error occurred: {e}")
    print("Please check if your token is correct and has the required scopes.")