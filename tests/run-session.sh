#!/usr/bin/env bash
# Starts a separate D-Bus, virtual compositor and HOME. Does not use the real session.
set -euo pipefail
task_repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
task_home=$(mktemp -d /tmp/island-kde-test.XXXXXX)
mkdir -p "$task_home/runtime" "$task_home/config" "$task_home/data" "$task_home/state" "$task_home/cache"
chmod 700 "$task_home/runtime"
export HOME=$task_home XDG_CONFIG_HOME=$task_home/config XDG_DATA_HOME=$task_home/data
export XDG_STATE_HOME=$task_home/state XDG_CACHE_HOME=$task_home/cache XDG_RUNTIME_DIR=$task_home/runtime
export XDG_CURRENT_DESKTOP=KDE XDG_SESSION_TYPE=wayland KDE_FULL_SESSION=true KDE_SESSION_VERSION=6
export XDG_DATA_DIRS=/usr/local/share:/usr/share ISLAND_REPO=$task_repo
export KWIN_COMPOSE=Q QSG_RHI_BACKEND=software QT_QUICK_BACKEND=software
unset DISPLAY WAYLAND_DISPLAY DBUS_SESSION_BUS_ADDRESS DBUS_STARTER_ADDRESS DBUS_STARTER_BUS_TYPE SESSION_MANAGER
echo "Isolated test HOME: $task_home"
# shellcheck disable=SC2016 # Variables intentionally expand inside the isolated child shell.
dbus-run-session -- bash -euc '
    "$ISLAND_REPO/install.sh" --no-apt --prepare-only
    exec kwin_wayland --virtual --width 1920 --height 1080 --no-lockscreen --no-global-shortcuts --no-kactivities \
        --exit-with-session "$ISLAND_REPO/tests/session-inner.sh"
'
