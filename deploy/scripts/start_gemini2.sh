#!/usr/bin/env bash
# Explicit camera capture only. Never invoked by selecting a dashboard profile.
set -euo pipefail
source /opt/ros/jazzy/setup.bash
if [[ -n "${ONIGIRI_ORBBEC_SETUP:-}" ]]; then
  source "$ONIGIRI_ORBBEC_SETUP"
fi
if ! ros2 pkg prefix orbbec_camera >/dev/null 2>&1; then
  echo "Driver orbbec_camera não instalado. Consulte docs/PLATAFORMAS_E_SENSORES.md." >&2
  exit 1
fi
exec ros2 launch orbbec_camera gemini2.launch.py camera_name:=camera \
  enable_color:=true enable_depth:=true enable_ir:=false \
  enable_point_cloud:=false enable_colored_point_cloud:=false \
  enable_accel:=true enable_gyro:=true
