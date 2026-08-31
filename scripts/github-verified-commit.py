#!/usr/bin/env python3
"""Create a GitHub-App-authored commit through the Git Database API.

No author, committer or signature fields are supplied. GitHub can therefore apply
its bot signature when the request is authenticated as a GitHub App. The script
checks the API's verification result and refuses to create the branch unless the
new commit is reported as verified.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://api.github.com"
API_VERSION = "2026-03-10"


def request(token, method, url, data=None):
    body = None if data is None else json.dumps(data).encode()
    req = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": "microtik-containers-bot/1",
            **({"Content-Type": "application/json"} if body is not None else {}),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            payload = response.read()
            return json.loads(payload) if payload else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise RuntimeError(f"GitHub API {method} {url}: HTTP {e.code}: {detail}") from e


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY"), required=False)
    ap.add_argument("--base", default="main")
    ap.add_argument("--branch", required=True)
    ap.add_argument("--message", required=True)
    ap.add_argument("--files", nargs="+", required=True)
    args = ap.parse_args()

    token = os.environ.get("GH_TOKEN")
    if not token:
        raise SystemExit("GH_TOKEN is required and must be a GitHub App installation token")
    if not args.repo or "/" not in args.repo:
        raise SystemExit("--repo OWNER/REPO or GITHUB_REPOSITORY is required")

    owner, repo = args.repo.split("/", 1)
    repo_root = Path.cwd().resolve()
    api_repo = f"{API}/repos/{owner}/{repo}"

    base_ref = request(token, "GET", f"{api_repo}/git/ref/heads/{urllib.parse.quote(args.base, safe='')}")
    parent_sha = base_ref["object"]["sha"]
    parent_commit = request(token, "GET", f"{api_repo}/git/commits/{parent_sha}")
    base_tree = parent_commit["tree"]["sha"]

    tree_entries = []
    for raw_path in args.files:
        path = Path(raw_path)
        full = (repo_root / path).resolve()
        try:
            full.relative_to(repo_root)
        except ValueError:
            raise SystemExit(f"Refusing path outside repository: {raw_path}")
        if not full.is_file():
            raise SystemExit(f"File does not exist: {raw_path}")
        encoded = base64.b64encode(full.read_bytes()).decode("ascii")
        blob = request(token, "POST", f"{api_repo}/git/blobs", {"content": encoded, "encoding": "base64"})
        tree_entries.append({"path": path.as_posix(), "mode": "100644", "type": "blob", "sha": blob["sha"]})

    tree = request(token, "POST", f"{api_repo}/git/trees", {"base_tree": base_tree, "tree": tree_entries})
    # Deliberately omit author, committer and signature. This is required for GitHub's
    # bot signature verification when authenticated as a GitHub App.
    commit = request(
        token,
        "POST",
        f"{api_repo}/git/commits",
        {"message": args.message, "tree": tree["sha"], "parents": [parent_sha]},
    )

    verification = commit.get("verification") or {}
    if verification.get("verified") is not True:
        raise SystemExit(
            "GitHub did not report the bot commit as Verified; refusing to create the branch. "
            f"reason={verification.get('reason', 'unknown')}"
        )

    request(
        token,
        "POST",
        f"{api_repo}/git/refs",
        {"ref": f"refs/heads/{args.branch}", "sha": commit["sha"]},
    )
    print(commit["sha"])
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
            f.write(f"sha={commit['sha']}\n")


if __name__ == "__main__":
    main()
