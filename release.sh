#!/usr/bin/env bash
set -euo pipefail

BUMP_TYPE="${1:-}"

if [[ ! "$BUMP_TYPE" =~ ^(patch|minor|major)$ ]]; then
  echo "Usage: ./release.sh [patch|minor|major]"
  exit 1
fi
if [[ -n $(git status --porcelain) ]]; then
  echo "Error: Working directory is not clean. Commit or stash changes first."
  exit 1
fi

echo "Syncing local main branch..."
git checkout main
git pull origin main

echo "Bumping version ($BUMP_TYPE)..."
uvx hatch version "$BUMP_TYPE"
NEW_VERSION=$(uvx hatch version)
TAG_NAME="v${NEW_VERSION}"
BRANCH_NAME="release/${TAG_NAME}"

echo "Creating and pushing to branch '${BRANCH_NAME}'..."
git checkout -b "$BRANCH_NAME"
git add src/streamdaq/__about__.py
git commit -m "chore(release): Bump version to ${NEW_VERSION}"
git push origin "$BRANCH_NAME"

echo "Attempting to create a PR..."
if command -v gh &> /dev/null; then
  gh pr create \
    --title "release: ${TAG_NAME}" \
    --body "Automated release bump to \`${NEW_VERSION}\`." \
    --base main \
    --head "$BRANCH_NAME"
  echo "Release PR created successfully: '${TAG_NAME}'"
else
  echo "GitHub CLI ('gh') not found. Please open a PR manually for '$BRANCH_NAME'."
fi

echo "======================================================================"
echo "Once the PR is merged into main, run these commands to trigger PyPI:"
echo ""
echo "  git checkout main"
echo "  git pull origin main"
echo "  git tag ${TAG_NAME}"
echo "  git push origin ${TAG_NAME}"
echo "======================================================================"
