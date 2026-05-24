#!/usr/bin/env bash
# One-time GitHub setup for develop + branch protection (Bucket 10).
# Requires: gh auth login with admin:repo_hook or repo admin scope.
set -euo pipefail

REPO="${GITHUB_REPOSITORY:-KaluMuso/zed-cv}"

echo "==> Ensuring develop exists from master"
git fetch origin master
if git ls-remote --exit-code --heads origin develop >/dev/null 2>&1; then
  echo "develop already on origin"
else
  git checkout master
  git pull origin master
  git checkout -b develop
  git push -u origin develop
fi

echo "==> Setting default branch to develop"
gh api "repos/${REPO}" -X PATCH -f default_branch=develop

echo "==> Done. Configure branch protection in GitHub UI if gh API payloads differ:"
echo "    - master: require PR, CI, no force-push; merge source develop only (ruleset)"
echo "    - develop: require PR, CI, squash merge"
echo "    See docs/branching.md"
