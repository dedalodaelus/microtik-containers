#!/usr/bin/env bash
set -euo pipefail

REPO="${REPO:-dedalodaelus/microtik-containers}"
MODE="${1:-}"

usage() {
  cat <<'USAGE'
Usage:
  REPO=owner/repo ./scripts/bootstrap-repository-gh.sh settings
  BOT_APP_CLIENT_ID=... BOT_APP_PRIVATE_KEY_FILE=/path/key.pem \
    REPO=owner/repo ./scripts/bootstrap-repository-gh.sh app-secrets
  REPO=owner/repo ./scripts/bootstrap-repository-gh.sh ruleset

Run "settings" and "app-secrets" before the first push. Run "ruleset" only
after the initial signed commit has reached main and the CI job named "required"
has completed at least once.
USAGE
}

need_gh() {
  command -v gh >/dev/null 2>&1 || { echo "gh is required" >&2; exit 1; }
  gh auth status --hostname github.com >/dev/null
}

repo_settings() {
  echo "Configuring repository settings for $REPO"
  gh repo edit "$REPO" \
    --description "Small community containers for MikroTik RouterOS, including ARMv5 builds." \
    --enable-issues \
    --enable-auto-merge \
    --enable-squash-merge \
    --enable-merge-commit \
    --enable-rebase-merge=false \
    --delete-branch-on-merge \
    --allow-update-branch \
    --squash-merge-commit-message pr-title

  for topic in mikrotik routeros buildroot nut armv5 containers; do
    gh repo edit "$REPO" --add-topic "$topic"
  done

  gh label create dependencies --repo "$REPO" --color 0366D6 --description "Dependency update" --force
  gh label create github-actions --repo "$REPO" --color 000000 --description "GitHub Actions dependency update" --force
  gh label create buildroot --repo "$REPO" --color 0E8A16 --description "Buildroot dependency update" --force

  # These are available on public GitHub repositories, but do not make the
  # rest of the bootstrap fail if the account/repository plan refuses them.
  gh repo edit "$REPO" --enable-secret-scanning || echo "WARNING: could not enable secret scanning" >&2
  gh repo edit "$REPO" --enable-secret-scanning-push-protection || echo "WARNING: could not enable push protection" >&2
}

app_secrets() {
  : "${BOT_APP_CLIENT_ID:?BOT_APP_CLIENT_ID is required}"
  : "${BOT_APP_PRIVATE_KEY_FILE:?BOT_APP_PRIVATE_KEY_FILE is required}"
  [[ -r "$BOT_APP_PRIVATE_KEY_FILE" ]] || { echo "Cannot read $BOT_APP_PRIVATE_KEY_FILE" >&2; exit 1; }

  echo "Storing GitHub App credentials for $REPO"
  gh variable set BOT_APP_CLIENT_ID --repo "$REPO" --body "$BOT_APP_CLIENT_ID"
  gh secret set BOT_APP_PRIVATE_KEY --repo "$REPO" < "$BOT_APP_PRIVATE_KEY_FILE"

  gh variable get BOT_APP_CLIENT_ID --repo "$REPO" >/dev/null
  gh secret list --repo "$REPO" --json name --jq '.[].name' | grep -Fx BOT_APP_PRIVATE_KEY >/dev/null
}

ruleset() {
  local existing
  existing="$(gh api "repos/${REPO}/rulesets" --jq '.[] | select(.name == "main-protection") | .id' | head -n1)"
  if [[ -n "$existing" ]]; then
    echo "Ruleset main-protection already exists as ID $existing; leaving it unchanged."
    return 0
  fi

  echo "Creating main-protection ruleset for $REPO"
  gh api --method POST \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2026-03-10" \
    "repos/${REPO}/rulesets" \
    --input .github/rulesets/main.json \
    --jq '{id,name,enforcement}'
}

need_gh
case "$MODE" in
  settings) repo_settings ;;
  app-secrets) app_secrets ;;
  ruleset) ruleset ;;
  *) usage; exit 2 ;;
esac
