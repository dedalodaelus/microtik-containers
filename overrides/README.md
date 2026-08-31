# Local overrides

This directory is for private/local configuration that should not be committed.

For NUT:

```bash
cp -a containers/nut/examples/override/. overrides/nut/
```

Edit the copied files, especially:

```text
overrides/nut/etc/nut/ups.conf
overrides/nut/etc/nut/upsd.users
```

Then build:

```bash
make nut-local
```

The override tree is merged over the public base rootfs overlay before Buildroot runs.

**Important:** a locally generated container image will contain the credentials present in your override. Treat that image as sensitive.
