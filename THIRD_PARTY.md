# Third-party software and licenses

The repository's own scripts and documentation are licensed under MIT, but generated container images include third-party software under their respective licenses.

The NUT image currently includes components such as:

- Buildroot-generated userspace
- BusyBox
- musl libc
- Network UPS Tools (NUT)
- libusb

Release builds run Buildroot's `legal-info` target and publish the resulting material as:

```text
nut-routeros-armv5-legal-info.tar.xz
```

This archive is intended to make license review and source-compliance work easier. Buildroot's own legal-info output should still be reviewed before redistribution because automated license metadata cannot replace legal review.
