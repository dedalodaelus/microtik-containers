#!/usr/bin/env bash
set -euo pipefail

usage() {
    echo "Usage: $0 <container> [--local-overrides]" >&2
    exit 2
}

[[ $# -ge 1 ]] || usage
container="$1"
shift

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
container_dir="${repo_root}/containers/${container}"

[[ -x "${container_dir}/build.sh" ]] || {
    echo "Unknown container or missing executable build.sh: ${container}" >&2
    exit 1
}

exec "${container_dir}/build.sh" "$@"
