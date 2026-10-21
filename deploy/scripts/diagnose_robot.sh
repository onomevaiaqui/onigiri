#!/usr/bin/env bash
# Read-only diagnostics; avoids dumping environment values or credentials.
set -uo pipefail
uname -m
cat /etc/os-release
for unit in onigiri-admin-web onigiri-udp onigiri-lidar; do
 systemctl is-active "$unit" || true
done
ls -l /dev/serial/by-id/ 2>/dev/null || true
df -h /home/onigiri
curl --max-time 3 -fsS http://127.0.0.1:8080/api/health || true
if [[ -f /opt/ros/jazzy/setup.bash ]]; then
 set +u; source /opt/ros/jazzy/setup.bash; set -u
 timeout 5 ros2 topic list -t || true
fi
