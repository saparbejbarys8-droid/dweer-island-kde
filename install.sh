#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail

task_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
install_deps=1
prepare_only=0
scale=0.9
photo_dir=""
for arg in "$@"; do
    case "$arg" in
        --no-apt) install_deps=0 ;;
        --prepare-only) prepare_only=1 ;;
        --scale=*) scale=${arg#*=} ;;
        --photo-dir=*) photo_dir=${arg#*=} ;;
        -h|--help)
            cat <<'HELP'
Usage: ./install.sh [--no-apt] [--prepare-only] [--scale=0.9|keep] [--photo-dir=/path]
Debian 13 KDE Plasma 6.3 / Wayland. Run as your normal user.
Installs dependencies and the complete desktop; wallpaper stays unchanged.
Without an active KDE session, applies automatically at your next KDE login.
--prepare-only builds/installs local assets without changing the desktop or scheduling apply.
HELP
            exit 0 ;;
        *) echo "Unknown option: $arg" >&2; exit 2 ;;
    esac
done
if (( EUID == 0 )); then
    echo 'Run ./install.sh as your normal desktop user, without sudo. It requests root only for apt.' >&2
    exit 1
fi
# shellcheck source=/dev/null
source /etc/os-release
if [[ ${ID:-} != debian || ${VERSION_ID:-} != 13 ]]; then
    echo 'Supported system: Debian 13 (trixie). No settings changed.' >&2
    exit 1
fi
if [[ $scale != keep ]] && ! awk -v n="$scale" 'BEGIN {exit !(n ~ /^[0-9]+([.][0-9]+)?$/ && n >= 0.75 && n <= 3)}'; then
    echo 'Scale must be keep or a number from 0.75 to 3.' >&2; exit 2
fi
if [[ -n $photo_dir && ! -d $photo_dir ]]; then
    echo "Photo directory does not exist: $photo_dir" >&2; exit 2
fi

if (( install_deps )); then
    mapfile -t packages < "$task_root/scripts/dependencies.txt"
    if command -v sudo >/dev/null; then
        sudo apt-get update
        sudo apt-get install -y "${packages[@]}"
        if [[ ! -e /etc/systemd/system/display-manager.service ]]; then
            sudo systemctl enable sddm
            sudo systemctl set-default graphical.target
        fi
    else
        echo 'sudo is unavailable; enter the root password for Debian package installation.'
        su -c "apt-get update && apt-get install -y ${packages[*]} && if [ ! -e /etc/systemd/system/display-manager.service ]; then systemctl enable sddm && systemctl set-default graphical.target; fi"
    fi
fi

task_data=${XDG_DATA_HOME:-$HOME/.local/share}
task_dest=$task_data/dweer-island-kde
mkdir -p -- "$task_dest"
if [[ $(realpath -- "$task_root/src") != $(realpath -m -- "$task_dest/src") ]]; then
    # Explicit allowlist: never copy home configuration, images, screenshots or backups.
    mkdir -p -- "$task_dest/src"
    cp -- "$task_root/src/"*.py "$task_root/src/"*.js "$task_dest/src/"
    rm -rf -- "$task_dest/src/fan"
    cp -R -- "$task_root/src/fan" "$task_dest/src/fan"
fi
python3 "$task_dest/src/theme.py" prepare
args=(--scale "$scale")
if [[ -n $photo_dir ]]; then args+=(--photo-dir "$photo_dir"); fi
if (( prepare_only )); then
    echo "Prepared at $task_dest. Your current desktop has not changed."
elif [[ ${XDG_CURRENT_DESKTOP:-} == *KDE* ]] && qdbus6 org.kde.plasmashell /PlasmaShell >/dev/null 2>&1; then
    python3 "$task_dest/src/theme.py" apply "${args[@]}"
else
    python3 "$task_dest/src/theme.py" schedule "${args[@]}"
    echo 'Installed. Log into Plasma (Wayland); the desktop will configure itself once.'
    echo 'If KDE was just installed from a text console, reboot first.'
fi
