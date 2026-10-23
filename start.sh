#!/usr/bin/env bash
# Quick start for the UR10e control UI and the drop contact test.
#
#   ./start.sh                     launch the GUI (installs dependencies on first run)
#   ./start.sh install             (re)create .venv and install dependencies
#   ./start.sh check               ping the robot and its RTDE port
#   ./start.sh drop-test [args]    home -> 100 mm above drop -> force-mode descent to contact
#   ./start.sh drop-test --dry-run resolve and print the poses without moving
#   ./start.sh drop-test --help    list all test options
#
# Robot IP: defaults to Config.DEFAULT_IP; override with ROBOT_IP=x.x.x.x ./start.sh ...
set -euo pipefail

cd "$(dirname "$(readlink -f "$0")")"

VENV=.venv
PY="$VENV/bin/python"
STAMP="$VENV/.requirements.stamp"
# ur-rtde publishes Linux wheels for CPython 3.7-3.12 only
PY_VERSION=3.12

log() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
die() { printf '\033[1;31mERROR:\033[0m %s\n' "$*" >&2; exit 1; }

find_python() {
    local v
    for v in 3.12 3.11 3.10; do
        if command -v "python$v" >/dev/null 2>&1; then
            command -v "python$v"
            return 0
        fi
    done
    return 1
}

create_venv() {
    local py uv
    rm -rf "$VENV"
    if py=$(find_python); then
        log "Creating $VENV with $py"
        "$py" -m venv "$VENV" || die "venv failed; try: sudo apt install python3-venv"
        return
    fi

    # No compatible system Python: let uv provide a managed CPython $PY_VERSION
    if command -v uv >/dev/null 2>&1; then
        uv=uv
    else
        log "No Python 3.10-3.12 found; bootstrapping uv into .tools/"
        python3 -m venv .tools || die "venv failed; try: sudo apt install python3-venv"
        .tools/bin/pip install -q --upgrade uv
        uv=.tools/bin/uv
    fi
    log "Creating $VENV with uv-managed Python $PY_VERSION"
    "$uv" venv --seed --python "$PY_VERSION" "$VENV"
}

install() {
    create_venv
    log "Installing requirements"
    "$PY" -m pip install -q --upgrade pip
    "$PY" -m pip install -r requirements.txt
    verify
    touch "$STAMP"
    log "Install complete"
}

verify() {
    log "Verifying imports"
    QT_QPA_PLATFORM=offscreen "$PY" - <<'EOF'
import sys
failed = []
for name in ("PyQt5.QtWidgets", "pyqtgraph", "numpy", "scipy", "rtde_control", "rtde_receive"):
    try:
        __import__(name)
        print(f"  ok   {name}")
    except Exception as exc:
        print(f"  FAIL {name}: {exc}")
        failed.append(name)
sys.exit(1 if failed else 0)
EOF
}

# Install on first run, or again when requirements.txt changed
ensure_env() {
    if [[ ! -x "$PY" || ! -f "$STAMP" || requirements.txt -nt "$STAMP" ]]; then
        install
    fi
}

robot_ip() {
    if [[ -n "${ROBOT_IP:-}" ]]; then
        echo "$ROBOT_IP"
    else
        "$PY" -c "from config import Config; print(Config.DEFAULT_IP)"
    fi
}

check() {
    local ip
    ip=$(robot_ip)
    log "Checking robot at $ip"
    if ping -c 2 -W 2 "$ip" >/dev/null 2>&1; then
        echo "  ok   network reachable"
    else
        die "$ip is not reachable (power, cable, IP, subnet?)"
    fi
    local port
    for port in 30004 30001; do
        if timeout 2 bash -c "echo > /dev/tcp/$ip/$port" 2>/dev/null; then
            echo "  ok   port $port open"
        else
            echo "  FAIL port $port closed (robot in Remote Control? RTDE enabled?)"
        fi
    done
}

drop_test() {
    local args=()
    [[ -n "${ROBOT_IP:-}" ]] && args+=(--ip "$ROBOT_IP")
    exec "$PY" test_scripts/test_home_to_drop_force_contact.py "${args[@]}" "$@"
}

cmd="${1:-gui}"
[[ $# -gt 0 ]] && shift

case "$cmd" in
    install)   install ;;
    gui)       ensure_env; exec "$PY" main.py "$@" ;;
    check)     ensure_env; check ;;
    drop-test) ensure_env; drop_test "$@" ;;
    -h|--help|help) sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//' ;;
    *)         die "Unknown command '$cmd' (try: ./start.sh help)" ;;
esac
