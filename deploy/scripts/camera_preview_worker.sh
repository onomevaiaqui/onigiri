#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/jazzy/setup.bash
if [[ -n "${ONIGIRI_ORBBEC_SETUP:-}" ]]; then source "$ONIGIRI_ORBBEC_SETUP"; fi
project_root="$(cd -- "$(dirname -- "$0")/../.." && pwd)"
exec /usr/bin/python3 "$project_root/software/admin_web/app/camera_preview_ros.py" "${1:?Destino ausente}" "${ONIGIRI_CAMERA_COLOR_TOPIC:-/camera/color/image_raw}"
