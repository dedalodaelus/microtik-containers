#!/usr/bin/env python3
"""Return the container components that should be rebuilt for a git change set."""
import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def all_containers():
    return [
        p.name
        for p in sorted((ROOT / "containers").iterdir())
        if p.is_dir() and (p / "metadata.env").is_file() and (p / "build.sh").is_file()
    ]


def git_changed(base, head):
    if not base or set(base) == {"0"}:
        return None
    proc = subprocess.run(
        ["git", "-C", str(ROOT), "diff", "--name-only", f"{base}..{head}"],
        check=True,
        text=True,
        capture_output=True,
    )
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def select(paths):
    all_names = all_containers()
    if paths is None:
        return all_names
    selected = set()
    shared_prefixes = ("scripts/", ".github/workflows/")
    shared_exact = {"Makefile"}
    for path in paths:
        if path in shared_exact or path.startswith(shared_prefixes):
            return all_names
        parts = path.split("/")
        if len(parts) >= 2 and parts[0] == "containers" and parts[1] in all_names:
            selected.add(parts[1])
    return sorted(selected)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    result = all_containers() if args.all else select(git_changed(args.base, args.head))
    print(json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()
