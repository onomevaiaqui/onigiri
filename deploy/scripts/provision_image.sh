#!/usr/bin/env bash
# Runs once inside a fresh Ubuntu 24.04 arm64 Raspberry Pi image (cloud-init).
set -euo pipefail
[[ "$(id -u)" == 0 ]] || { echo 'Execute como root'; exit 1; }
source /etc/os-release
[[ "$VERSION_ID" == 24.04 && "$(dpkg --print-architecture)" == arm64 ]] || { echo 'Requer Ubuntu 24.04 arm64'; exit 1; }
root=/home/onigiri/onigiri
[[ ! -e "$root/software" ]] || { echo 'Instalação existente preservada; use o atualizador'; exit 1; }
apt-get update
apt-get install -y curl ca-certificates gnupg python3-venv python3-yaml avahi-daemon
install -d -m 755 /etc/apt/keyrings
curl -fsSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /etc/apt/keyrings/ros.asc
printf '%s\n' 'deb [arch=arm64 signed-by=/etc/apt/keyrings/ros.asc] http://packages.ros.org/ros2/ubuntu noble main' > /etc/apt/sources.list.d/ros2.list
apt-get update
apt-get install -y ros-jazzy-ros-base ros-jazzy-rplidar-ros python3-colcon-common-extensions
mkdir -p "$root"
cp -a /opt/onigiri-bootstrap/payload/. "$root/"
chown -R onigiri:onigiri "$root"
sudo -u onigiri bash "$root/deploy/scripts/install_admin_web.sh"
sudo -u onigiri bash "$root/deploy/scripts/install_robot_runtime.sh"
sudo -u onigiri bash "$root/deploy/scripts/install_lidar_odometry.sh"
if [[ -f /opt/onigiri-bootstrap/platform.json ]]; then
 install -o onigiri -g onigiri -m 600 /opt/onigiri-bootstrap/platform.json "$root/data/platform.json"
fi
python3 - "$root/data/platform.json" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]);config=json.loads(p.read_text())
model=Path('/proc/device-tree/model').read_bytes().decode(errors='ignore')
config['computer']='raspberry5' if 'Raspberry Pi 5' in model else 'raspberry4'
p.write_text(json.dumps(config))
PY
chown onigiri:onigiri "$root/data/platform.json"
if [[ -f /opt/onigiri-bootstrap/with-orbbec ]]; then
 sudo -u onigiri bash "$root/deploy/scripts/install_orbbec.sh"
 sudo -u onigiri bash "$root/deploy/scripts/install_rgbd.sh"
 printf '\nONIGIRI_CAMERA_AUTOSTART=1\n' >> /etc/onigiri/admin.env
fi
install -m 644 "$root/deploy/systemd/onigiri-lidar.service" /etc/systemd/system/onigiri-lidar.service
systemctl daemon-reload
systemctl enable --now avahi-daemon.service onigiri-lidar.service
systemctl restart onigiri-admin-web.service
mkdir -p /var/lib/onigiri
dpkg-query -W > /var/lib/onigiri/packages.tsv
printf '%s\n' 'ready' > /var/lib/onigiri/provisioned
# No motor service is enabled. Commission dimensions, serial and emergency stop first.
