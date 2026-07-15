#!/bin/bash
# Push full project to GitHub (run once in Terminal — browser login will open).
set -e
cd "$(dirname "$0")"

GITHUB_URL="https://github.com/yashwantreddyvarra-bot/dish-ai-knowledge-operations.git"

git remote remove github 2>/dev/null || true
git remote add github "$GITHUB_URL"

echo "Pushing to GitHub..."
git push -u github gitlab-push:feature/dish-doc-automation

echo ""
echo "Done! Open:"
echo "  https://github.com/yashwantreddyvarra-bot/dish-ai-knowledge-operations/tree/feature/dish-doc-automation"
