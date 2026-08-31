# Security notes for RouterOS containers

## NUT

NUT's `upsd` service listens on TCP/3493 in the default NUT image. Treat it as a management service.

Recommended rules:

- allow TCP/3493 only from trusted clients;
- do not publish TCP/3493 through WAN destination NAT;
- use a unique password for each deployment where authenticated `upsmon` access is required;
- keep `upsd.users` in `overrides/nut/`, not in Git;
- keep the container `privileged=no` when USB passthrough via `devices=` is sufficient.

## Release verification

Every automated release publishes a SHA256 checksum. Verify it before importing an image into RouterOS.

## Buildroot upstream verification

The automated Buildroot updater accepts only the official **Stable** row and verifies the corresponding `.tar.xz.sign` with fingerprints pinned in `security/buildroot-release-signers.txt`. The tarball must match the SHA256 contained in that signed manifest. A signer rotation therefore requires an explicit reviewed change to the trusted fingerprint list.
