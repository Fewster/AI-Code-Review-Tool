import os
import requests
import subprocess
import textwrap

# these will use the secrets applied to repositories
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_EVENT_PATH = os.environ["GITHUB_EVENT_PATH"]
GITHUB_REPOSITORY = os.environ["GITHUB_REPOSITORY"]

def run(cmd):
    return subprocess.check_output(cmd, shell=True, text=True)

def truncate(text, limit=800):
    return text[:limit].rstrip() if len(text) > limit else text

# get pull-request info
import json
with open(GITHUB_EVENT_PATH, "r") as f:
    event = json.load(f)

pr_number = event["pull_request"]["number"]
repo_owner, repo_name = GITHUB_REPOSITORY.split("/")

# get diff
run("git fetch origin +refs/pull/*/merge")
diff = run(f"git diff origin/main...HEAD")

if not diff.strip():
    review_text = "No code changes detected."
else:

  # OpenAI prompt for code reveiw
    prompt = f"""
You are a senior software engineer performing a pull request review.

Rules:
- Be concise and practical
- Focus on correctness, maintainability, security, and performance
- Do NOT exceed 800 characters total
- Use bullet points
- No praise or filler

Code diff:
{diff}
"""

    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
      # gpt-5 doesn't support temperature, top_p, etc.
        json={
            "model": "gpt-5-nano", #change based on need (defaulted to gpt-5)
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1200, #modify this for short summary returns
        },
        timeout=60, 
    )
# OpenAI response 
    response.raise_for_status()
    review_text = response.json()["choices"][0]["message"]["content"]
    review_text = truncate(review_text, 800)

# post pull-request comment
comment_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues/{pr_number}/comments"

requests.post(
    comment_url,
    headers={
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    },
    json={
        "body": f"### Automated Code Review\n\n{review_text}" # change this based on default output required
    },
).raise_for_status()
