#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/jazzy/setup.bash
root="$(cd -- "$(dirname -- "$0")/../.." && pwd)"
exec /usr/bin/python3 "$root/software/robot_runtime/bridge_node.py" "${1:?Diretório ausente}"
