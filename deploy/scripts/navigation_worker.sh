#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/jazzy/setup.bash
if [[ -n "${ONIGIRI_ODOMETRY_SETUP:-}" ]]; then source "$ONIGIRI_ODOMETRY_SETUP"; fi
root="$(cd -- "$(dirname -- "$0")/../.." && pwd)"
exec /usr/bin/python3 "$root/software/robot_runtime/stack.py" "${1:?Diretório ausente}" "${2:?Mapa ausente}"
