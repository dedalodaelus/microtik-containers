# Repository bootstrap

Canonical repository:

```text
https://github.com/dedalodaelus/microtik-containers
```

The detailed Spanish `gh` bootstrap/upload guide is distributed alongside the repository archive. This file records the policy expected by the workflows. A maintainer helper is also included at `scripts/bootstrap-repository-gh.sh` for repository settings, App credentials and ruleset creation.

## GitHub App

Create and install a repository-scoped App such as `microtik-containers-bot` with:

- Contents: read/write
- Pull requests: read/write
- Issues: read/write
- Metadata: read

Do not grant a ruleset bypass. Store:

```text
Variable: BOT_APP_CLIENT_ID
Secret:   BOT_APP_PRIVATE_KEY
```

## Default branch policy

Push the initial **human-signed** commit and let `CI / required` run at least once before creating the ruleset from `.github/rulesets/main.json`. The ruleset requires pull requests, Verified signatures, the `required` CI status check, resolved review threads, and blocks force pushes. Squash and merge commits are both allowed: squash is preferred for human/App-owned PRs, while merge commits remain available for third-party bot PRs where GitHub's signed-commit squash restrictions would otherwise be awkward.

The repository does not grant automation bypass.

## Release bootstrap

`.release-please-manifest.json` intentionally starts as `{}` and `containers/nut/VERSION` starts at `0.0.0`. An initial commit such as:

```text
feat(nut): add ARMv5 NUT container
```

lets Release Please propose the first NUT release at `0.1.0`.

See `docs/github-app.md`, `docs/automation.md`, and `docs/release-policy.md`.
