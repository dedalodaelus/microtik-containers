# MikroTik Containers

Community-oriented, small Linux containers for MikroTik RouterOS.

Repository: https://github.com/dedalodaelus/microtik-containers

The repository is intentionally a **multi-container monorepo**. Each container lives in `containers/<name>/`, has independent build logic/documentation/versioning, and is released independently through Release Please.

## Available containers

| Container | Architecture | Purpose | Status |
|---|---|---|---|
| [NUT](containers/nut/README.md) | `linux/arm/v5` | Network UPS Tools server with USB HID support | Initial release |

## Layout

```text
.
├── containers/                  # Independently releasable containers
│   └── nut/
├── overrides/                   # Local/private git-ignored overrides
├── scripts/                     # Shared build and automation helpers
├── tests/                       # Automation tests
├── docs/                        # Project documentation
├── release-please-config.json
├── .release-please-manifest.json
└── .github/
    ├── dependabot.yml
    ├── rulesets/main.json
    └── workflows/
```

## Build locally

On Debian/Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y   build-essential cpio rsync file bc curl xz-utils unzip python3 podman
```

Build NUT:

```bash
make nut
```

Artifacts:

```text
dist/nut/
```

Private override build:

```bash
cp -a containers/nut/examples/override/. overrides/nut/
# Edit overrides/nut/etc/nut/*
make nut-local
```

`overrides/` is ignored by Git to reduce the risk of committing credentials.

## Automation

The repository combines:

- **CI**: validates Verified commits and builds affected containers;
- **weekly health rebuilds**: rebuild every container without releasing;
- **Dependabot**: maintains GitHub Actions dependencies;
- **Buildroot updater**: checks the official Stable Buildroot release daily, verifies its PGP-signed checksum against pinned release keys, opens a Verified GitHub App PR, auto-merges same-series patch updates after CI, and leaves new series for manual review;
- **Release Please**: independent Conventional Commit/SemVer releases for every container;
- **release asset builds**: build the component at its release tag and attach artifacts automatically.

See:

- [Automation architecture](docs/automation.md)
- [Release policy](docs/release-policy.md)
- [GitHub App setup](docs/github-app.md)
- [Repository bootstrap](docs/repository-bootstrap.md)
- [Adding another container](docs/adding-a-container.md)

## Commit policy

The recommended default-branch ruleset included in `.github/rulesets/main.json` requires:

- pull requests;
- Verified commit signatures;
- the `required` CI check;
- mandatory Verified signatures on the default branch;
- squash or merge PRs (squash preferred for human/App-owned PRs);
- no force pushes.

The automation App is **not** a bypass actor.

Use Conventional Commit PR titles, for example:

```text
feat(nut): add support for another UPS profile
fix(nut): fix driver startup
```

## Releases

Tags and releases are component-prefixed:

```text
nut-v0.1.0
<future-container>-v1.0.0
```

The initial repository starts with `containers/nut/VERSION=0.0.0`. A signed initial `feat(nut): ...` commit causes Release Please to propose the first `0.1.0` release PR.

## Security

- Never commit UPS passwords, tokens, RouterOS credentials or private keys.
- Official release images contain no default NUT authentication credentials.
- Keep RouterOS containers unprivileged unless a documented requirement says otherwise.
- Do not expose NUT TCP/3493 directly to the Internet.

See [SECURITY.md](SECURITY.md) and [docs/security.md](docs/security.md).

## License

Repository-authored scripts and documentation are MIT licensed. Generated images include third-party software under their respective licenses; release builds include Buildroot `legal-info` output. See [THIRD_PARTY.md](THIRD_PARTY.md).
