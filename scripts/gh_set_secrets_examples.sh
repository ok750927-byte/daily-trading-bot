#!/usr/bin/env bash
# Example commands to set repository secrets using GitHub CLI (`gh`).
# Replace <owner>/<repo> with your repository, and provide the new values.

REPO="ok750927-byte/daily-trading-bot"  # repository owner/repo

echo "Setting secrets in repo: $REPO"

# Usage: export NEW_KIS_KEY="..." NEW_KIS_SECRET="..." then run this script
if [ -z "$NEW_KIS_KEY" ] || [ -z "$NEW_KIS_SECRET" ]; then
  echo "Please export NEW_KIS_KEY and NEW_KIS_SECRET before running."
  echo "Example: export NEW_KIS_KEY=abc123 NEW_KIS_SECRET=def456"
  exit 1
fi

gh secret set KIS_APP_KEY --body "$NEW_KIS_KEY" --repo "$REPO"
gh secret set KIS_APP_SECRET --body "$NEW_KIS_SECRET" --repo "$REPO"

# Discord webhook
if [ -n "$NEW_DISCORD_WEBHOOK" ]; then
  gh secret set DISCORD_WEBHOOK_URL --body "$NEW_DISCORD_WEBHOOK" --repo "$REPO"
fi

echo "Done. Trigger a workflow run or push an empty commit to validate."
