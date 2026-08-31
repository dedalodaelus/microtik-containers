# Contributing

## Pull requests

- Use a branch; do not push directly to `main`.
- Every commit must be cryptographically signed and show **Verified** on GitHub.
- Use a Conventional Commit PR title because squash merge makes the PR title the durable commit subject on `main`.
- Keep changes scoped to the relevant container when possible.
- Never include production credentials or private override files.

Examples:

```text
feat(nut): add generic HID example
fix(nut): correct runtime directory permissions
docs(nut): clarify RouterOS USB passthrough
deps(buildroot): update Buildroot to 2026.05.3
```

## Local validation

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q scripts tests
find scripts containers -type f -name '*.sh' -print0 | xargs -0 -r -n1 bash -n
make nut
```

## Release management

Do not manually edit component changelogs for a normal release. Release Please manages `VERSION`, component `CHANGELOG.md`, tags and GitHub Releases.
