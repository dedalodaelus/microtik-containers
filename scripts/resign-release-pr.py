#!/usr/bin/env python3
"""Rewrite a Release Please PR head as one Verified GitHub-App commit.

Release Please does not expose a native commit-signing switch. This helper keeps
Release Please responsible for calculating the release changes, then reproduces
those exact file changes in a commit created through GitHub's Git Database API.
The request is authenticated as the repository GitHub App and deliberately omits
custom author/committer/signature fields, allowing GitHub's bot signature model.

The existing PR branch is force-updated only after GitHub reports the replacement
commit as verification.verified=true.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request

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
            "User-Agent": "microtik-containers-release-signer/1",
            **({"Content-Type": "application/json"} if body is not None else {}),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            payload = response.read()
            return json.loads(payload) if payload else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise RuntimeError(f"GitHub API {method} {url}: HTTP {exc.code}: {detail}") from exc


def paged(token, url):
    page = 1
    out = []
    while True:
        sep = "&" if "?" in url else "?"
        batch = request(token, "GET", f"{url}{sep}per_page=100&page={page}")
        out.extend(batch)
        if len(batch) < 100:
            return out
        page += 1


def contents(token, api_repo, path, ref):
    quoted = urllib.parse.quote(path, safe="/")
    data = request(token, "GET", f"{api_repo}/contents/{quoted}?ref={urllib.parse.quote(ref, safe='')}")
    if data.get("type") != "file" or data.get("encoding") != "base64":
        raise RuntimeError(f"Unsupported release file response for {path}")
    return base64.b64decode(data["content"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY"))
    ap.add_argument("--pr", type=int, required=True)
    args = ap.parse_args()
    token = os.environ.get("GH_TOKEN")
    if not token:
        raise SystemExit("GH_TOKEN must be a GitHub App installation token")
    if not args.repo or "/" not in args.repo:
        raise SystemExit("--repo OWNER/REPO or GITHUB_REPOSITORY is required")

    owner, repo = args.repo.split("/", 1)
    api_repo = f"{API}/repos/{owner}/{repo}"
    pr = request(token, "GET", f"{api_repo}/pulls/{args.pr}")
    labels = {item["name"] for item in pr.get("labels", [])}
    if "autorelease: pending" not in labels:
        raise SystemExit(f"PR #{args.pr} is not an autorelease: pending Release Please PR")
    if pr["base"]["ref"] != "main":
        raise SystemExit(f"PR #{args.pr} does not target main")
    if pr["head"]["repo"]["full_name"].lower() != args.repo.lower():
        raise SystemExit("Refusing to rewrite a PR branch from a fork")

    head_sha = pr["head"]["sha"]
    head_commit = request(token, "GET", f"{api_repo}/commits/{head_sha}")
    verification = head_commit["commit"].get("verification") or {}
    if verification.get("verified") is True:
        print(f"PR #{args.pr} head is already Verified: {head_sha}")
        return

    base_sha = pr["base"]["sha"]
    base_commit = request(token, "GET", f"{api_repo}/git/commits/{base_sha}")
    base_tree = base_commit["tree"]["sha"]
    files = paged(token, f"{api_repo}/pulls/{args.pr}/files")
    if not files:
        raise SystemExit(f"PR #{args.pr} has no changed files")

    tree_entries = []
    for item in files:
        path = item["filename"]
        status = item["status"]
        if status == "renamed" and item.get("previous_filename"):
            tree_entries.append({"path": item["previous_filename"], "mode": "100644", "type": "blob", "sha": None})
        if status == "removed":
            tree_entries.append({"path": path, "mode": "100644", "type": "blob", "sha": None})
            continue
        raw = contents(token, api_repo, path, head_sha)
        blob = request(
            token,
            "POST",
            f"{api_repo}/git/blobs",
            {"content": base64.b64encode(raw).decode("ascii"), "encoding": "base64"},
        )
        tree_entries.append({"path": path, "mode": "100644", "type": "blob", "sha": blob["sha"]})

    tree = request(token, "POST", f"{api_repo}/git/trees", {"base_tree": base_tree, "tree": tree_entries})
    commit = request(
        token,
        "POST",
        f"{api_repo}/git/commits",
        {"message": pr["title"], "tree": tree["sha"], "parents": [base_sha]},
    )
    v = commit.get("verification") or {}
    if v.get("verified") is not True:
        raise SystemExit(
            "Replacement Release Please commit was not reported Verified; refusing branch update. "
            f"reason={v.get('reason', 'unknown')}"
        )

    head_ref = urllib.parse.quote(pr["head"]["ref"], safe="/")
    request(token, "PATCH", f"{api_repo}/git/refs/heads/{head_ref}", {"sha": commit["sha"], "force": True})
    print(f"PR #{args.pr}: replaced {head_sha} with Verified commit {commit['sha']}")


if __name__ == "__main__":
    main()
