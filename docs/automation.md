# Automation architecture

The repository is a multi-container monorepo. Each independently releasable container lives in `containers/<name>/` and is versioned independently.

## CI

`CI` runs on pull requests and pushes. It validates scripts/configuration, enforces Conventional Commit style PR titles, checks that every PR commit is reported by GitHub as `Verified`, discovers affected containers, rebuilds only those containers, and exposes a stable `required` status check for the default-branch ruleset.

A weekly **Health rebuild** rebuilds every container without creating a release. This catches upstream download/toolchain/runner breakage even when the repository has not changed.

## Dependabot

Dependabot maintains GitHub Actions dependencies through `.github/dependabot.yml`. Dependabot commits are still checked by CI for GitHub `Verified` status. Because the default ruleset requires signed commits, automation must never replace a verified dependency commit with an unsigned local commit.

## Buildroot updater

The daily updater reads the official `https://buildroot.org/download.html` page and selects the row explicitly labelled **Stable**. Candidate/RC releases are never selected merely because they have a higher version number.

For every `containers/*/metadata.env` with `BUILDROOT_TRACK=stable`, the updater:

1. detects the new Stable version;
2. downloads the official `.tar.xz` and `.tar.xz.sign`;
3. imports only the fingerprints in `security/buildroot-release-signers.txt`;
4. verifies the PGP clearsigned checksum manifest;
5. downloads the tarball and verifies its SHA256 against the signed value;
6. updates `BUILDROOT_VERSION` and `BUILDROOT_SHA256`;
7. creates the change as a GitHub-App-authored Verified commit.

The GPG keyserver is only a transport for keys: fingerprints are pinned in the repository. A keyserver cannot silently substitute a different signing key without a fingerprint collision. If verification fails, the updater fails closed.

If Buildroot rotates release-signing keys, the updater intentionally stops. A maintainer must independently verify the new official fingerprint, add it to `security/buildroot-release-signers.txt` through a normal reviewed/signed PR, and only then allow automated updates to resume.

Policy:

- same-series patch (`2026.05.2 -> 2026.05.3`): `fix(buildroot): ...`, PR + required CI + App-authenticated auto-merge;
- new Stable series (`2026.05.x -> 2026.08`): `feat(buildroot): ...`, PR + required CI + manual maintainer decision;
- Candidate/RC: ignored;
- `BUILDROOT_TRACK=locked`: ignored.

For a manually approved new-series bot PR, run the **Merge bot PR** workflow. This lets the same GitHub App that authored the automation PR perform the squash merge while the signed-commit ruleset remains enabled.

## Verified bot commits

`scripts/github-verified-commit.py` creates blobs, a tree and a commit through the Git Database REST API with a GitHub App installation token. It deliberately omits custom author, committer and signature fields and refuses to create a branch unless GitHub returns `verification.verified=true`.

## Release Please

Release Please runs in manifest/monorepo mode. Components have independent tags such as `nut-v0.1.0`. The App token is used instead of the special workflow `GITHUB_TOKEN`, so Release Please-created resources can trigger downstream workflows.

Because commit-signing is mandatory and Release Please itself does not expose a native signing switch, `scripts/resign-release-pr.py` normalizes each open `autorelease: pending` PR after Release Please runs. It reproduces the exact PR file changes as a single GitHub-App-authored commit and force-updates the release branch only after GitHub reports the replacement commit as Verified. CI runs again on the synchronized PR.

When a maintainer is ready to publish, the **Merge bot PR** workflow can be started with the Release Please PR number. The App requests a squash auto-merge after verifying all PR commits. Once the release PR lands, Release Please creates the component tag/release and `release-assets.yml` builds and attaches the `.tar`, SHA256, build-info and Buildroot legal-info assets.

## Adding another container

Add `containers/<name>/` with `metadata.env` and an executable `build.sh`, then register it in `release-please-config.json`. Shared CI, health rebuild and release asset workflows discover buildable container directories automatically.
