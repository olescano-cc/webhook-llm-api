from flask import Flask
import requests
import json

GITHUB_TOKEN = "your key"
LLM_API_URL = "your llm endpoint"

app = Flask(__name__)

def read_prompt_file(file_path):
    """Reads the contents of the prompt file"""
    with open(file_path, 'r') as file:
        return file.read()

def call_llm(prompt):
    body = {"model": "llama3.2", "prompt": prompt, "stream": False}
    return requests.post(LLM_API_URL, json=body).json()

def add_or_update_pr_description(owner, repo, pr_number):
    prompt_template = read_prompt_file('prompt_pr_description.txt')
    diff = requests.get(f"https://patch-diff.githubusercontent.com/raw/{owner}/{repo}/pull/{pr_number}.diff").text
    final_prompt = prompt_template.replace("diff-var", diff)
   
    response = call_llm(final_prompt)
   
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Content-Type": "application/json"}
    requests.post(f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}", json={"body": response['response']}, headers=headers)

def add_pr_comment(owner, repo, pr_number):
    prompt_template = read_prompt_file('prompt.txt')
    diff = requests.get(f"https://patch-diff.githubusercontent.com/raw/{owner}/{repo}/pull/{pr_number}.diff").text
    final_prompt = prompt_template.replace("diff-var", diff)

    response = call_llm(final_prompt)

    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Content-Type": "application/json"}
    requests.post(f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments",  json={"body": response['response']}, headers=headers)

def review_pr_lines(owner, repo, pr_number):
    prompt_template = read_prompt_file('prompt_file_lines.txt')
    files_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"

    # Headers for authentication
    headers = {
        "Authorization": f"Bearer {"another_user_key"}",
        "Accept": "application/vnd.github.v3+json"
    }

    # Fetch all the files changed in the pull request
    response = requests.get(files_url, headers=headers)

    if response.status_code == 200:
        files_data = response.json()
        
        # Define the general review and any comments on specific lines or files
        comments = []
        for file in files_data:
            # Here, you can inspect the diff and decide where to comment
            # For simplicity, we'll add a generic comment on each file
            final_prompt = prompt_template.replace("diff-var", file["patch"])

            response = call_llm(final_prompt)
            reviews = json.loads(response['response'])

            comments = comments + reviews
        
        # Submit a review with the "REQUEST_CHANGES" event
        review_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
        review_data = {
            "event": "REQUEST_CHANGES",  # Can also use "APPROVE" or "COMMENT"
            "body": "This pull request requires changes. Please review the changes in the files.",
            "comments": comments  # Add the comments on specific lines or files
        }

        # Send the review to GitHub
        review_response = requests.post(review_url, headers=headers, json=review_data)
        print(review_response)
    else:
        print(f"Failed to fetch files: {response.status_code}")


@app.route('/webhook')
def webhook():
    add_or_update_pr_description('owner', 'repo_name', 'pr_number')
    add_pr_comment('owner', 'repo_name', 'pr_number')
    review_pr_lines('owner', 'repo_name', 'pr_number')

    return {"response": 'OK'}

if __name__ == '__main__':
    app.run(debug=True)
