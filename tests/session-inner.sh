#!/usr/bin/env bash
set -euo pipefail
plasmashell >"$HOME/plasma-initial.log" 2>&1 &
trap 'qdbus6 org.kde.plasmashell /MainApplication org.qtproject.Qt.QCoreApplication.quit >/dev/null 2>&1 || true' EXIT
for ((i=0;i<90;i++)); do
    task_ready=$(qdbus6 org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript 'print(desktops().length)' 2>/dev/null || true)
    if [[ $task_ready =~ [1-9] ]]; then
        break
    fi
    sleep 1
done
python3 "$ISLAND_REPO/tests/session_checks.py"
