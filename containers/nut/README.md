# NUT for MikroTik RouterOS — ARMv5

A very small [Network UPS Tools (NUT)](https://networkupstools.org/) server image built with Buildroot for MikroTik RouterOS devices that require an **ARMv5-compatible userspace**.

The image provides:

- musl
- BusyBox
- libusb
- NUT `upsd`
- NUT `upsdrvctl`
- NUT `upsc`
- `usbhid-ups`

It intentionally does not include systemd, OpenRC, a package manager or a Linux kernel.

## Tested hardware/software

Development has been validated with:

- MikroTik hEX S E60iUGS
- EN7562CT platform reported by RouterOS as ARM
- RouterOS 7.24.1
- `container` package 7.24.1
- Eaton Ellipse ECO 800 USB HID UPS
- Buildroot 2026.05.2
- NUT 2.8.4 as provided by that Buildroot release

Other devices may work, but are not claimed as tested until reported and verified.

## Why Buildroot instead of Alpine?

This image targets ARMv5. Current Alpine ARM ports start at ARMv6 (`armhf`) or ARMv7, so a normal Alpine mini-rootfs is not an ARMv5 base. Buildroot lets this project produce a deliberately small ARM926T/EABI5 userspace instead.

## Official image defaults

The public image contains no passwords.

Default NUT configuration:

```ini
[ups]
    driver = usbhid-ups
    port = auto
```

`upsd` listens on:

```text
0.0.0.0:3493
```

Read-only `upsc` queries do not require a default user. If you need `upsmon`, authenticated commands or a custom UPS name/vendor filter, build a local image with an override as described below.

---

# Download a release

Open this repository's **Releases** page and select a `nut-v...` release.

Download:

```text
nut-routeros-armv5.tar
nut-routeros-armv5.tar.sha256
```

Verify on Linux:

```bash
sha256sum -c nut-routeros-armv5.tar.sha256
```

---

# RouterOS installation

## 1. Requirements

The router must have:

- RouterOS **7.20 or newer** for hardware passthrough through `devices=`;
- the matching `container` package installed;
- enough storage for the extracted image;
- physical access to enable the container feature in device-mode;
- the UPS visible under `/system/resource/hardware` if USB passthrough is required.

Check:

```routeros
/system/package/print where name="container"
/system/device-mode/print
```

If needed:

```routeros
/system/device-mode/update container=yes
```

RouterOS requires physical confirmation for this change.

The `devices=` hardware passthrough feature arrived with RouterOS 7.20. This project was validated on 7.24.1; RouterOS 7.24 also includes a relevant fix for device overrides appearing correctly under `/dev`, so 7.24+ is recommended for USB NUT deployments.

## 2. Identify the USB UPS

Connect the UPS and run:

```routeros
/system/resource/hardware/print detail where type=usb
```

Example:

```text
location="1-1" vendor="EATON" name="Ellipse ECO" ...
```

Record the `location`. In the examples below it is `1-1`; **use the value from your router**.

## 3. Create a VETH

Example dedicated NUT subnet/VLAN:

```text
VLAN:    42
Gateway: 192.168.42.1/29
NUT:     192.168.42.3/29
```

Create the VETH:

```routeros
/interface/veth/add \
    name=veth-nut \
    address=192.168.42.3/29 \
    gateway=192.168.42.1
```

## 4. VLAN-aware bridge example

If `bridge-LAN` already carries VLAN 42, add the VETH as an access port:

```routeros
/interface/bridge/port/add \
    bridge=bridge-LAN \
    interface=veth-nut \
    pvid=42 \
    frame-types=admit-only-untagged-and-priority-tagged \
    ingress-filtering=yes \
    comment="NUT container VLAN42"
```

Do not blindly overwrite an existing bridge VLAN member list. Verify your current VLAN table first:

```routeros
/interface/bridge/vlan/print detail where vlan-ids=42
/interface/bridge/port/print detail where interface=veth-nut
```

With bridge VLAN filtering, the PVID/access-port configuration is sufficient for RouterOS to classify untagged VETH traffic into VLAN 42. If you maintain explicit static `untagged=` lists, add `veth-nut` while preserving all existing members.

## 5. Upload the image

Upload:

```text
nut-routeros-armv5.tar
```

through WinBox/WebFig **Files**, or another trusted transfer method.

Verify:

```routeros
/file/print where name~"nut-routeros"
```

## 6. Create the container

Using USB location `1-1` from the earlier example:

```routeros
/container/add \
    file=nut-routeros-armv5.tar \
    interface=veth-nut \
    root-dir=nut-root \
    name=nut \
    hostname=nut \
    logging=yes \
    start-on-boot=yes \
    devices=1-1:""
```

Keep the container unprivileged; USB passthrough through `devices=` is sufficient for the tested Eaton HID setup.

Wait until extraction finishes:

```routeros
/container/print
```

Then start it:

```routeros
/container/start nut
```

## 7. Verify locally

```routeros
/container/shell nut
```

Inside the container:

```sh
upsc ups@localhost
```

A working UPS should return variables such as:

```text
battery.charge
battery.runtime
ups.load
ups.status
```

## 8. Verify remotely

From a trusted client:

```bash
upsc ups@192.168.42.3
```

Restrict TCP/3493 to trusted networks. Do not expose it directly to the Internet.

---

# Custom configuration / overrides

The repository contains a private-local override mechanism.

Copy the example:

```bash
cp -a containers/nut/examples/override/. overrides/nut/
```

Edit:

```text
overrides/nut/etc/nut/ups.conf
overrides/nut/etc/nut/upsd.users
```

Then build:

```bash
make nut-local
```

The files in `overrides/nut/` are ignored by Git.

Example Eaton configuration:

```ini
[EL800USBDIN]
    driver = usbhid-ups
    port = auto
    vendorid = 0463
    desc = "Eaton Ellipse ECO 800"
```

Example client account:

```ini
[slave]
    password = REPLACE_WITH_A_STRONG_PASSWORD
    upsmon secondary
```

The same credentials must be configured on the remote `upsmon` client:

```ini
MONITOR EL800USBDIN@192.168.42.3 1 slave REPLACE_WITH_A_STRONG_PASSWORD secondary
```

A locally built image containing `upsd.users` credentials is sensitive even if the source override is git-ignored.

---

# Build locally

From the repository root:

```bash
make nut
```

For a private override build:

```bash
make nut-local
```

Output:

```text
dist/nut/nut-routeros-armv5.tar
dist/nut/nut-routeros-armv5.tar.sha256
dist/nut/nut-routeros-armv5-build-info.txt
dist/nut/nut-routeros-armv5-legal-info.tar.xz
```

The build checks that `usbhid-ups`, `upsc`, `upsdrvctl` and `upsd` are 32-bit ARM EABI5 binaries before packaging the RouterOS image.

---

# Releases

NUT releases use tags such as:

```text
nut-v0.1.0
```

Release Please manages the component version, `nut-v...` tag and GitHub Release from Conventional Commits. When the Release Please release is published, the `Release assets` workflow rebuilds this component at that exact tag and attaches the generated image, checksum, build information and legal-info archive.

---

# Storage notes

MikroTik generally recommends appropriate storage for containers. This image is deliberately tiny and low-write, but flash endurance and available space remain the responsibility of the device owner. Prefer external storage where the router and deployment make that practical.

# Limitations

- The official artifact is specifically built for `linux/arm/v5` / ARM EABI5.
- USB support depends on RouterOS exposing the UPS in `/system/resource/hardware` and allowing it through `devices=`.
- No default authentication user is included in the public image.
- This project does not claim compatibility with every MikroTik ARM router or every NUT-supported UPS.
