# Security Policy

## Reporting a vulnerability

Use GitHub private vulnerability reporting / Security Advisories when available.

Do not publish credentials, private keys, production `upsd.users` files or other secrets in public issues.

## Repository automation

- Default-branch commits are expected to be **Verified**.
- The Buildroot updater creates commits through GitHub's Git Database API using a repository-scoped GitHub App and refuses to publish a branch if GitHub does not report the new commit as verified.
- Release Please uses the same App token; its open release PR heads are checked for signature verification.
- The automation App has no ruleset bypass.
- Dependabot is limited to supported dependency ecosystems (currently GitHub Actions).

## Container security principles

- Official images do not ship authentication passwords.
- Keep RouterOS containers unprivileged whenever possible.
- Restrict NUT TCP/3493 to trusted networks.
- Do not expose NUT directly to the public Internet.
- Verify release assets with the accompanying SHA256 file.
- Treat locally built images containing `upsd.users` credentials as secrets.
