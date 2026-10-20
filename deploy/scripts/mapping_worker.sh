#!/usr/bin/env bash
# Invoked by the panel with fixed operations; never drives motors.
set -euo pipefail
set +u
source /opt/ros/jazzy/setup.bash
if [[ -n "${ONIGIRI_ROS_SETUP:-}" ]]; then source "$ONIGIRI_ROS_SETUP"; fi
if [[ -n "${ONIGIRI_ODOMETRY_SETUP:-}" ]]; then source "$ONIGIRI_ODOMETRY_SETUP"; fi
set -u
case "${1:-}" in
  start-lidar-odometry)
    project_root="$(cd -- "$(dirname -- "$0")/../.." && pwd)"
    exec /usr/bin/python3 "$project_root/software/admin_web/app/lidar_odometry.py"
    ;;
  start-stationary)
    project_root="$(cd -- "$(dirname -- "$0")/../.." && pwd)"
    exec /usr/bin/python3 "$project_root/software/admin_web/app/stationary_slam.py"
    ;;
  preview)
    project_root="$(cd -- "$(dirname -- "$0")/../.." && pwd)"
    exec /usr/bin/python3 "$project_root/software/admin_web/app/map_preview_ros.py" "${2:?Arquivo da prévia ausente}"
    ;;
  start-experimental)
    # Recovered historical launch: installed SLAM defaults, real wall clock.
    # TF must already exist; never invent odometry or start motor services.
    project_root="$(cd -- "$(dirname -- "$0")/../.." && pwd)"
    exec /usr/bin/python3 "$project_root/software/admin_web/app/slam_runtime.py"
    ;;
  start)
    test -f "${ONIGIRI_SLAM_PARAMS:?Configure o YAML SLAM validado}"
    project_root="$(cd -- "$(dirname -- "$0")/../.." && pwd)"
    exec /usr/bin/python3 "$project_root/software/admin_web/app/slam_runtime.py" "$ONIGIRI_SLAM_PARAMS"
    ;;
  save)
    exec ros2 run nav2_map_server map_saver_cli -f "${2:?Destino ausente}" --fmt pgm --ros-args -p save_map_timeout:=10.0 -p map_subscribe_transient_local:=true
    ;;
  *) exit 2 ;;
esac
