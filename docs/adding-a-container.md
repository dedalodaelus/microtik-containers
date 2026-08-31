# Adding another container

This repository is designed as a multi-container monorepo.

## 1. Directory structure

Create:

```text
containers/<name>/
├── README.md
├── CHANGELOG.md
├── VERSION
├── metadata.env
└── build.sh
```

`build.sh` must place release-ready assets under:

```text
dist/<name>/
```

Shared tooling belongs under `scripts/`.

## 2. Automatic discovery

A directory is considered buildable when it contains both:

```text
metadata.env
build.sh
```

CI and the weekly health rebuild discover these directories automatically.

## 3. Overrides

For local configuration use:

```text
overrides/<name>/
```

Keep its contents ignored by Git and provide safe public examples under:

```text
containers/<name>/examples/override/
```

Never require real credentials in tracked files.

## 4. Release Please component

Add a package entry to `release-please-config.json`:

```json
"containers/<name>": {
  "release-type": "simple",
  "component": "<name>",
  "package-name": "<name>",
  "initial-version": "0.1.0",
  "version-file": "VERSION",
  "changelog-path": "CHANGELOG.md",
  "include-component-in-tag": true,
  "include-v-in-tag": true
}
```

Release Please then uses tags:

```text
<name>-vMAJOR.MINOR.PATCH
```

The release asset workflow automatically maps this tag back to `containers/<name>`.

## 5. Buildroot tracking

For Buildroot-based containers choose explicitly:

```text
BUILDROOT_TRACK=stable
BUILDROOT_AUTO_MERGE=patch
```

or lock the component:

```text
BUILDROOT_TRACK=locked
BUILDROOT_AUTO_MERGE=never
```

## 6. Architecture

Do not assume every MikroTik ARM device supports the same ISA. Validate and document the exact target architecture for each image.
