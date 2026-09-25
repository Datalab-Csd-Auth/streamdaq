#!/usr/bin/env bash
set -euo pipefail

BUMP_TYPE="${1:-}"

if [[ ! "$BUMP_TYPE" =~ ^(patch\vert{}minor\vert{}major)$ ]]; then
  echo "Usage: ./release.sh [patch|minor|major]"
  exit 1
fi

# 1. Ensure working directory is clean
if [[ -n $(git status --porcelain) ]]; then
  echo "Error: Working directory is not clean. Commit or stash changes first."
  exit 1
fi

# 2. Sync main
echo "Syncing local main branch..."
git checkout main
git pull origin main

# 3. Bump version using Hatch
echo "Bumping version ($BUMP_TYPE)..."
NEW_VERSION=$(uvx hatch version "$BUMP_TYPE")
TAG_NAME="v${NEW_VERSION}"
BRANCH_NAME="release/${TAG_NAME}"

# 4. Create branch and commit
git checkout -b "$BRANCH_NAME"
git add src/streamdaq/__about__.py
git commit -m "chore(release): bump version to ${NEW_VERSION}"

# 5. Push branch
git push origin "$BRANCH_NAME"

# 6. Create PR via GitHub CLI
if command -v gh &> /dev/null; then
  gh pr create \
    --title "release: ${TAG_NAME}" \
    --body "Automated release bump to \`${NEW_VERSION}\`." \
    --base main \
    --head "$BRANCH_NAME"
  echo "Release PR created successfully!"
else
  echo "GitHub CLI ('gh') not found. Please open a PR manually for '$BRANCH_NAME'."
fi

echo ""
echo "======================================================================"
echo " RELEASE PR CREATED: ${TAG_NAME}"
echo "======================================================================"
echo "Once the PR is merged into main, run these commands to trigger PyPI:"
echo ""
echo "  git checkout main"
echo "  git pull origin main"
echo "  git tag ${TAG_NAME}"
echo "  git push origin ${TAG_NAME}"
echo "======================================================================"
