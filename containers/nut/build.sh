#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
container_dir="${repo_root}/containers/nut"
source "${container_dir}/metadata.env"
version="$(tr -d '[:space:]' < "${container_dir}/VERSION")"

use_overrides=0
if [[ "${1:-}" == "--local-overrides" ]]; then
    use_overrides=1
    shift
fi
[[ $# -eq 0 ]] || { echo "Unexpected arguments: $*" >&2; exit 2; }

for cmd in curl tar make gcc g++ cpio rsync file xz podman sha256sum; do
    command -v "$cmd" >/dev/null || {
        echo "Missing required command: $cmd" >&2
        exit 1
    }
done

jobs="${JOBS:-$(nproc 2>/dev/null || echo 2)}"
build_dir="${repo_root}/.build/nut"
cache_dir="${BR2_DL_DIR:-${repo_root}/.cache/buildroot-dl}"
dist_dir="${repo_root}/dist/nut"
archive="${repo_root}/.cache/buildroot-${BUILDROOT_VERSION}.tar.xz"
src_dir="${build_dir}/buildroot-${BUILDROOT_VERSION}"
output_dir="${build_dir}/output"
external_dir="${build_dir}/br2-external"

mkdir -p "${build_dir}" "${cache_dir}" "${dist_dir}" "$(dirname "${archive}")"
rm -rf "${dist_dir:?}"/* "${external_dir}" "${output_dir}"
mkdir -p "${output_dir}"

if [[ ! -f "${archive}" ]]; then
    echo "Downloading Buildroot ${BUILDROOT_VERSION}..."
    curl -fL --retry 3 --retry-delay 2 \
        "https://buildroot.org/downloads/buildroot-${BUILDROOT_VERSION}.tar.xz" \
        -o "${archive}"
fi

echo "${BUILDROOT_SHA256}  ${archive}" | sha256sum -c -

if [[ ! -d "${src_dir}" ]]; then
    tar -C "${build_dir}" -xf "${archive}"
fi

cp -a "${container_dir}/buildroot-external" "${external_dir}"

if [[ ${use_overrides} -eq 1 ]]; then
    override_dir="${repo_root}/overrides/nut"
    if find "${override_dir}" -type f ! -name '.gitkeep' -print -quit | grep -q .; then
        echo "Applying local override: ${override_dir}"
        cp -a "${override_dir}/." "${external_dir}/board/nut/rootfs-overlay/"
    else
        echo "--local-overrides requested but overrides/nut contains no override files." >&2
        exit 1
    fi
else
    # Public builds must not accidentally gain a real password.
    if grep -RniE '^[[:space:]]*password[[:space:]]*=[[:space:]]*[^#[:space:]]+' \
        "${external_dir}/board/nut/rootfs-overlay/etc/nut"; then
        echo "Refusing public build: tracked NUT configuration contains a password." >&2
        exit 1
    fi
fi

source_date_epoch="${SOURCE_DATE_EPOCH:-$(git -C "${repo_root}" log -1 --format=%ct 2>/dev/null || date +%s)}"
export SOURCE_DATE_EPOCH="${source_date_epoch}"

make -C "${src_dir}" O="${output_dir}" BR2_EXTERNAL="${external_dir}" \
    "${BUILDROOT_DEFCONFIG}"
make -C "${src_dir}" O="${output_dir}" BR2_DL_DIR="${cache_dir}" -j"${jobs}"

# Validate the binaries that matter for this image.
for binary in \
    "${output_dir}/target/usr/bin/usbhid-ups" \
    "${output_dir}/target/usr/bin/upsc" \
    "${output_dir}/target/usr/sbin/upsdrvctl" \
    "${output_dir}/target/usr/sbin/upsd"; do
    result="$(file "$binary")"
    echo "$result"
    grep -q 'ELF 32-bit' <<<"$result" || { echo "Not a 32-bit ELF: $binary" >&2; exit 1; }
    grep -q 'ARM' <<<"$result" || { echo "Not ARM: $binary" >&2; exit 1; }
    grep -q 'EABI5' <<<"$result" || { echo "Not EABI5: $binary" >&2; exit 1; }
done

rootfs="${output_dir}/images/rootfs.tar"
[[ -s "${rootfs}" ]] || { echo "Buildroot did not produce rootfs.tar" >&2; exit 1; }

image="${IMAGE_REPOSITORY}:${version}-${IMAGE_ARCH}${IMAGE_VARIANT}"
podman image rm -f "${image}" >/dev/null 2>&1 || true
podman import \
    --os linux \
    --arch "${IMAGE_ARCH}" \
    --variant "${IMAGE_VARIANT}" \
    --change "ENTRYPOINT [\"${IMAGE_ENTRYPOINT}\"]" \
    "${rootfs}" "${image}" >/dev/null

inspect="$(podman image inspect "${image}" --format 'OS={{.Os}} ARCH={{.Architecture}} ENTRYPOINT={{json .Config.Entrypoint}}')"
echo "$inspect"
grep -q 'OS=linux' <<<"$inspect"
grep -q 'ARCH=arm' <<<"$inspect"
grep -q "${IMAGE_ENTRYPOINT}" <<<"$inspect"

asset="${dist_dir}/${OUTPUT_BASENAME}.tar"
podman save --format docker-archive -o "${asset}" "${image}"
(
    cd "${dist_dir}"
    sha256sum "${OUTPUT_BASENAME}.tar" > "${OUTPUT_BASENAME}.tar.sha256"
)

# Generate Buildroot legal information for redistribution review.
make -C "${src_dir}" O="${output_dir}" BR2_DL_DIR="${cache_dir}" legal-info
if [[ -d "${output_dir}/legal-info" ]]; then
    tar -C "${output_dir}" -cJf "${dist_dir}/${OUTPUT_BASENAME}-legal-info.tar.xz" legal-info
fi

nut_version="$(sed -n 's/^NUT_VERSION[[:space:]]*=[[:space:]]*//p' "${src_dir}/package/nut/nut.mk" | head -n1 || true)"
commit="$(git -C "${repo_root}" rev-parse HEAD 2>/dev/null || echo unknown)"
rootfs_size="$(du -h "${rootfs}" | awk '{print $1}')"
image_size="$(du -h "${asset}" | awk '{print $1}')"

cat > "${dist_dir}/${OUTPUT_BASENAME}-build-info.txt" <<EOF
Container release: ${version}
Buildroot: ${BUILDROOT_VERSION}
NUT: ${nut_version:-unknown}
Target: linux/${IMAGE_ARCH}/${IMAGE_VARIANT}
Buildroot CPU: ARM926T / ARM EABI5
Entrypoint: ${IMAGE_ENTRYPOINT}
Rootfs tar size: ${rootfs_size}
RouterOS image archive size: ${image_size}
Source commit: ${commit}
SOURCE_DATE_EPOCH: ${SOURCE_DATE_EPOCH}
Local overrides included: $([[ ${use_overrides} -eq 1 ]] && echo yes || echo no)
EOF

echo
echo "Build complete:"
ls -lh "${dist_dir}"
