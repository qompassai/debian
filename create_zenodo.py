#!/usr/bin/env python3
import re
import json
import subprocess
import os
import sys
import tempfile

# Check if README.md exists
if not os.path.exists('README.md'):
    print("Error: README.md does not exist in the current directory.")
    sys.exit(1)

# Read README.md content
try:
    with open('README.md', 'r') as file:
        readme_content = file.read()
except Exception as e:
    print(f"Error reading README.md: {e}")
    sys.exit(1)

# Extract title (first line starting with # )
title_match = re.search(r'^# (.+)$', readme_content, re.MULTILINE)
title = title_match.group(1) if title_match else ""

# Extract Description section content
section_name = "Description"
pattern = rf'^## {re.escape(section_name)}\n(.+?)(?=^## |\Z)'
section_match = re.search(pattern, readme_content, re.MULTILINE | re.DOTALL)
description = section_match.group(1).strip() if section_match else ""

# Convert markdown description to HTML using pandoc
with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.md') as tmp_md:
    tmp_md.write(description)
    tmp_md_path = tmp_md.name

html_description_path = tmp_md_path.replace('.md', '.html')

try:
    # Run pandoc to convert markdown to html
    subprocess.run(['pandoc', '-f', 'markdown', '-t', 'html', tmp_md_path, '-o', html_description_path], check=True)
    
    # Read the html description
    with open(html_description_path, 'r') as f:
        html_description = f.read()
except Exception as e:
    print(f"Error processing description with pandoc: {e}")
    os.remove(tmp_md_path)
    if os.path.exists(html_description_path):
        os.remove(html_description_path)
    sys.exit(1)

# Get the current folder name as repo name if git remote isn't set yet
try:
    git_remote_url = subprocess.check_output(['git', 'remote', 'get-url', 'origin'], text=True).strip()
    
    # Extract org and repo from git remote url
    org = "qompassai"  # default org override
    repo = "your-repository-name"
    
    match = re.search(r'github.com[:/](.+?)/(.+?)(?:\.git)?$', git_remote_url)
    if match:
        org = match.group(1)
        repo = match.group(2)
except Exception as e:
    # If git remote not set, use current directory name
    org = "qompassai"
    repo = os.path.basename(os.getcwd())

# Build zenodo json
zenodo_json = {
    "title": title,
    "description": html_description,
    "license": ["AGPL-3.0", "Q-CDA-1.0"],
    "upload_type": "software",
    "access_right": "open",
    "version": "1.0.0",
    "creators": [
        {
            "name": "Porter, Matthew A.",
            "affiliation": "Qompass AI",
            "orcid": "https://0000-0002-0302-4812"
        }
    ],
    "keywords": ["AI", "Quantum", "Post-Quantum Cryptography", "Healthcare", "Education"],
    "related_identifiers": [
        {
            "identifier": f"https://github.com/{org}/{repo}",
            "relation": "isSupplementTo",
            "resource_type": "software"
        }
    ],
    "communities": [
        {"identifier": "qompass"}
    ]
}

# Write to .zenodo.json
try:
    with open('.zenodo.json', 'w') as f:
        json.dump(zenodo_json, f, indent=2)
    print(".zenodo.json updated successfully with dynamic title, description, and repo URL.")
except Exception as e:
    print(f"Error writing .zenodo.json: {e}")

# Clean up temporary files
try:
    os.remove(tmp_md_path)
    os.remove(html_description_path)
except Exception:
    pass
