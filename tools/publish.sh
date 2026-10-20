#!/usr/bin/env bash
# Builds index.html from the CURRENT thesis main and pushes it to the site's main.
# Used by both workflows (thesis repo: update-site.yml; site repo: build.yml), so
# there is one way to publish. Run from the root of a site checkout:
#   tools/publish.sh <thesis checkout> "<commit message>"
# The thesis checkout must be a git clone whose "origin" can be fetched.
# If someone else pushed to the site in the meantime, the push is rejected;
# then both repos are refreshed and the page is rebuilt, so a stale build
# can never overwrite a newer one.
set -euo pipefail
thesis=$1; message=$2
git fetch --quiet origin main
if [ -n "$(git log --oneline FETCH_HEAD..HEAD)" ]; then
  echo "This site checkout has commits that are not on GitHub yet; push them first (the pipeline publishes)." >&2
  exit 1
fi
for attempt in 1 2 3 4 5; do
  git -C "$thesis" fetch --quiet --depth 1 origin main
  git -C "$thesis" checkout --quiet --detach FETCH_HEAD
  sha=$(git -C "$thesis" rev-parse --short HEAD)
  python3 tools/build_site.py --thesis "$thesis" 2> warnings.txt
  cat warnings.txt
  if [ -s warnings.txt ] && [ -n "${GITHUB_STEP_SUMMARY:-}" ] && [ "$attempt" = 1 ]; then
    { echo "### Website build warnings"; echo; sed 's/^/- /' warnings.txt; } >> "$GITHUB_STEP_SUMMARY"
  fi
  rm -f warnings.txt
  if git diff --quiet; then
    echo "Website already shows thesis $sha."
    exit 0
  fi
  git config user.name "github-actions[bot]"
  git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
  git commit --quiet -am "Sync from thesis $sha: $message"
  if git push --quiet origin HEAD:main; then
    echo "Published thesis $sha."
    exit 0
  fi
  echo "Push rejected (someone else updated the site); refreshing and rebuilding (attempt $attempt)."
  git fetch --quiet origin main
  git reset --quiet --hard FETCH_HEAD
done
echo "Could not publish after 5 attempts." >&2
exit 1
