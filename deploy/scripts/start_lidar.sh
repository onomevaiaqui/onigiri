#!/usr/bin/env bash
# Start only the LiDAR selected in the persisted Onigiri profile.
set -euo pipefail
profile=/home/onigiri/onigiri/data/platform.json
read_profile() {
  python3 - "$profile" <<'PY'
import json, sys
try:
    value=json.load(open(sys.argv[1], encoding="utf-8"))
except (FileNotFoundError, json.JSONDecodeError):
    value={}
print(value.get("lidar_model", "rplidar"))
print(value.get("lidar_port", ""))
PY
}
mapfile -t profile_values < <(read_profile)
model="${profile_values[0]}"
port="${profile_values[1]:-/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0}"
case "$model" in
  rplidar)
    exec ros2 launch rplidar_ros rplidar.launch.py "serial_port:=$port"
    ;;
  generic_scan)
    echo "LiDAR externo configurado: aguardando um publicador ROS 2 em /scan."
    exec sleep infinity
    ;;
  *)
    echo "O perfil seleciona $model. Instale e habilite o driver correspondente antes de iniciar este serviço."
    exec sleep infinity
    ;;
esac
