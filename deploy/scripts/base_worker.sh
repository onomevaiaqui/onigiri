#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/jazzy/setup.bash
root="$(cd -- "$(dirname -- "$0")/../.." && pwd)"
exec /usr/bin/python3 "$root/software/robot_runtime/base_node.py"
