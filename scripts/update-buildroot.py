#!/usr/bin/env python3
"""Detect Buildroot's official Stable release and update tracked containers.

The source of truth is the row explicitly labelled "Stable" on
https://buildroot.org/download.html. Candidate/RC releases are ignored.

For a new Stable release the updater:
1. downloads the official .tar.xz and .tar.xz.sign files over HTTPS;
2. imports only explicitly pinned Buildroot release-signing fingerprints;
3. verifies the clearsigned Buildroot checksum manifest with GnuPG;
4. verifies the downloaded tarball SHA256 against the signed checksum;
5. pins that SHA256 in each stable-tracking container's metadata.env.

If the upstream page format changes, a signature is not trusted, or any hash
check fails, the updater fails closed and does not modify the repository.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOWNLOAD_PAGE = "https://buildroot.org/download.html"
DOWNLOADS = "https://buildroot.org/downloads"
SIGNERS_FILE = ROOT / "security" / "buildroot-release-signers.txt"
KEYSERVER = os.environ.get("BUILDROOT_GPG_KEYSERVER", "hkps://keyserver.ubuntu.com")
VERSION_RE = re.compile(r"\b(\d{4}\.\d{2}(?:\.\d+)?)\b")
SHA256_RE = re.compile(r"^SHA256:\s+([0-9a-fA-F]{64})\s+(\S+)\s*$", re.MULTILINE)


class TableRows(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self._row = None
        self._cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cell is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None


@dataclass
class Component:
    name: str
    metadata: Path
    values: dict[str, str]


def fetch_bytes(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "microtik-containers-buildroot-bot/1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def stable_version(html: str) -> str:
    parser = TableRows()
    parser.feed(html)
    matches = []
    for row in parser.rows:
        if row and row[0].strip().lower() == "stable":
            for cell in row[1:]:
                # Skip a series field such as 2026.05.x.
                if re.search(r"\b\d{4}\.\d{2}\.x\b", cell, re.IGNORECASE):
                    continue
                for match in VERSION_RE.finditer(cell):
                    matches.append(match.group(1))
            break
    # The first actual release in the Stable row is the intended value, but
    # require at least one match and reject candidate strings before returning.
    for version in matches:
        if "-rc" not in version:
            return version
    raise RuntimeError("Could not identify a Buildroot Stable release")


def parse_env(path: Path) -> dict[str, str]:
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


def components() -> list[Component]:
    out = []
    for metadata in sorted((ROOT / "containers").glob("*/metadata.env")):
        values = parse_env(metadata)
        out.append(Component(metadata.parent.name, metadata, values))
    return out


def version_tuple(version: str):
    parts = version.split(".")
    if len(parts) not in (2, 3) or not all(part.isdigit() for part in parts):
        raise ValueError(f"Unsupported Buildroot version: {version}")
    return tuple(int(x) for x in parts + (["0"] if len(parts) == 2 else []))


def same_series(a: str, b: str) -> bool:
    aa = version_tuple(a)
    bb = version_tuple(b)
    return aa[:2] == bb[:2]


def replace_env(path: Path, replacements: dict[str, str]):
    lines = path.read_text(encoding="utf-8").splitlines()
    seen = set()
    out = []
    for line in lines:
        if "=" in line and not line.lstrip().startswith("#"):
            key = line.split("=", 1)[0]
            if key in replacements:
                out.append(f"{key}={replacements[key]}")
                seen.add(key)
                continue
        out.append(line)
    missing = set(replacements) - seen
    if missing:
        raise RuntimeError(f"Missing keys in {path}: {', '.join(sorted(missing))}")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def trusted_signers(path: Path = SIGNERS_FILE) -> list[str]:
    signers = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip().replace(" ", "").upper()
        if not line or line.startswith("#"):
            continue
        if not re.fullmatch(r"[0-9A-F]{40}", line):
            raise RuntimeError(f"Invalid Buildroot signer fingerprint in {path}: {line}")
        signers.append(line)
    if not signers:
        raise RuntimeError(f"No trusted Buildroot signing fingerprints in {path}")
    return signers


def parse_signed_sha256(text: str, tarball_name: str) -> str:
    matches = [(digest.lower(), name) for digest, name in SHA256_RE.findall(text)]
    exact = [digest for digest, name in matches if name == tarball_name]
    if len(exact) != 1:
        raise RuntimeError(f"Signed manifest did not contain exactly one SHA256 for {tarball_name}")
    return exact[0]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_release(version: str) -> tuple[str, str]:
    """Return (sha256, signer fingerprint) after PGP + tarball verification."""
    if not shutil.which("gpg"):
        raise RuntimeError("gpg is required to verify Buildroot release signatures")

    tarball = f"buildroot-{version}.tar.xz"
    tar_url = f"{DOWNLOADS}/{tarball}"
    sig_url = f"{tar_url}.sign"
    signers = trusted_signers()

    with tempfile.TemporaryDirectory(prefix="buildroot-verify-") as td:
        td = Path(td)
        gnupg = td / "gnupg"
        gnupg.mkdir(mode=0o700)
        sig_path = td / f"{tarball}.sign"
        tar_path = td / tarball
        payload_path = td / "signed-checksums.txt"
        sig_path.write_bytes(fetch_bytes(sig_url))
        tar_path.write_bytes(fetch_bytes(tar_url))

        env = os.environ.copy()
        env["GNUPGHOME"] = str(gnupg)
        for fingerprint in signers:
            subprocess.run(
                ["gpg", "--batch", "--keyserver", KEYSERVER, "--recv-keys", fingerprint],
                env=env,
                check=True,
                stdout=subprocess.DEVNULL,
            )

        result = subprocess.run(
            [
                "gpg", "--batch", "--status-fd", "1", "--decrypt",
                "--output", str(payload_path), str(sig_path),
            ],
            env=env,
            check=True,
            text=True,
            capture_output=True,
        )
        # VALIDSIG reports the signing-key fingerprint first and, for a
        # signing subkey, may also include the primary-key fingerprint as the
        # last field. Trust the signature only when either fingerprint maps to
        # one of our explicitly pinned Buildroot release keys. Multiple valid
        # signatures are accepted (Buildroot release manifests can be signed
        # by more than one maintainer).
        trusted_valid = []
        all_valid = []
        for line in result.stdout.splitlines():
            if line.startswith("[GNUPG:] VALIDSIG "):
                fields = line.split()
                if len(fields) >= 3:
                    signing_fpr = fields[2].upper()
                    primary_fpr = fields[-1].upper() if re.fullmatch(r"[0-9A-F]{40}", fields[-1].upper()) else ""
                    all_valid.append(signing_fpr)
                    trusted = next((fpr for fpr in (primary_fpr, signing_fpr) if fpr in signers), "")
                    if trusted:
                        trusted_valid.append(trusted)
        if not trusted_valid:
            raise RuntimeError(
                "Buildroot signature was not made by a pinned release key: "
                f"valid_signatures={all_valid}"
            )

        signed_text = payload_path.read_text(encoding="utf-8", errors="strict")
        signed_digest = parse_signed_sha256(signed_text, tarball)
        actual_digest = sha256_file(tar_path)
        if actual_digest != signed_digest:
            raise RuntimeError(
                f"Buildroot tarball SHA256 mismatch: signed={signed_digest} actual={actual_digest}"
            )
        return actual_digest, ",".join(sorted(set(trusted_valid)))


def set_output(key: str, value: str):
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as f:
            f.write(f"{key}={value}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="update metadata.env files in place")
    ap.add_argument("--page-file", help="test/debug using a local copy of download.html")
    args = ap.parse_args()

    if args.page_file:
        page = Path(args.page_file).read_text(encoding="utf-8")
    else:
        page = fetch_bytes(DOWNLOAD_PAGE).decode("utf-8", errors="replace")
    latest = stable_version(page)

    tracked = [c for c in components() if c.values.get("BUILDROOT_TRACK", "locked") == "stable"]
    outdated = [c for c in tracked if c.values.get("BUILDROOT_VERSION") != latest]

    report = {
        "latest": latest,
        "changed": bool(outdated),
        "containers": [c.name for c in outdated],
        "updates": [],
        "update_kind": "none",
        "auto_merge": False,
        "signer": "",
    }

    if outdated:
        latest_tuple = version_tuple(latest)
        for c in outdated:
            current = c.values.get("BUILDROOT_VERSION", "")
            if version_tuple(current) >= latest_tuple:
                raise RuntimeError(f"Refusing downgrade/non-forward update for {c.name}: {current} -> {latest}")

        digest, signer = verify_release(latest)
        kinds = []
        auto_policies = []
        for c in outdated:
            current = c.values["BUILDROOT_VERSION"]
            kind = "patch" if same_series(current, latest) else "series"
            kinds.append(kind)
            auto_policies.append(c.values.get("BUILDROOT_AUTO_MERGE", "never"))
            report["updates"].append({"container": c.name, "from": current, "to": latest, "kind": kind})
            if args.apply:
                replace_env(c.metadata, {"BUILDROOT_VERSION": latest, "BUILDROOT_SHA256": digest})

        report["update_kind"] = "series" if "series" in kinds else "patch"
        report["auto_merge"] = report["update_kind"] == "patch" and all(
            policy in ("patch", "all") for policy in auto_policies
        )
        report["sha256"] = digest
        report["signer"] = signer

    print(json.dumps(report, indent=2, sort_keys=True))
    set_output("latest", report["latest"])
    set_output("changed", str(report["changed"]).lower())
    set_output("containers", json.dumps(report["containers"], separators=(",", ":")))
    set_output("update_kind", report["update_kind"])
    set_output("auto_merge", str(report["auto_merge"]).lower())
    set_output("changed_files", ",".join(f"containers/{name}/metadata.env" for name in report["containers"]))
    set_output("signer", report["signer"])


if __name__ == "__main__":
    main()
