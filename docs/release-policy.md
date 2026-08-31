# Release and rebuild policy

## Build types

| Type | Trigger | Builds | Creates a release |
|---|---|---:|---:|
| Pull-request CI | PR | affected containers | No |
| Push CI | push to `main`/`devel` | affected containers | No |
| Health rebuild | weekly | all containers | No |
| Release build | Release Please publishes a component release | released container | Yes, assets are attached |

Buildroot download caching only caches source downloads. Build outputs/root filesystems are rebuilt on fresh GitHub-hosted runners.

## Versioning

Release Please uses Conventional Commits and independent component versions. Examples:

```text
feat(nut): add configurable poll interval
fix(nut): create runtime directory before starting NUT
deps(buildroot): update Buildroot to 2026.05.3
```

Typical SemVer effect:

- `fix` / `deps`: patch;
- `feat`: minor;
- breaking change: according to Release Please's configured pre-1.0 strategy, minor while the component remains below 1.0.

## Buildroot updates

Stable Buildroot point releases are treated as low-risk dependency updates and may auto-merge after CI. A new stable Buildroot series always requires a manual merge because it can change the toolchain, libc and package versions even when compilation remains successful.

## Reproducibility boundary

The Buildroot version and tarball SHA256 are pinned, Buildroot reproducible mode is enabled, and CI starts from a clean output directory. GitHub-hosted runner images and distro package versions are not completely immutable, and the final Podman archive is not claimed to be bit-for-bit reproducible across all future runner versions.
