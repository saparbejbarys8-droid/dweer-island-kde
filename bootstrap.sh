#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail
task_repo=saparbejbarys8-droid/dweer-island-kde
task_version=v1.0.0
task_tmp=$(mktemp -d)
trap 'rm -rf -- "$task_tmp"' EXIT
task_url="https://github.com/$task_repo/archive/refs/tags/$task_version.tar.gz"
if command -v curl >/dev/null; then
    curl --fail --location --retry 3 --output "$task_tmp/source.tar.gz" "$task_url"
elif command -v wget >/dev/null; then
    wget -O "$task_tmp/source.tar.gz" "$task_url"
else
    echo 'Install curl or wget first.' >&2; exit 1
fi
tar -xzf "$task_tmp/source.tar.gz" -C "$task_tmp"
"$task_tmp/dweer-island-kde-${task_version#v}/install.sh" "$@"
