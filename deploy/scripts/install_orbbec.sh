#!/usr/bin/env bash
# Optional pinned source build for Jazzy; does not start a camera or motors.
set -eo pipefail
[[ "$(id -un)" == onigiri ]] || { echo 'Execute como onigiri'; exit 1; }
revision=c153462518ad674650bafa4464fda72c27ab797a
workspace=/home/onigiri/onigiri-orbbec/c153462
sudo apt-get update
sudo apt-get install -y git build-essential cmake python3-colcon-common-extensions python3-rosdep libgflags-dev nlohmann-json3-dev libdw-dev libssl-dev libusb-1.0-0-dev libudev-dev libgoogle-glog-dev libgl1 libopencv-dev \
 ros-jazzy-image-transport ros-jazzy-image-transport-plugins ros-jazzy-compressed-image-transport ros-jazzy-image-publisher ros-jazzy-camera-info-manager ros-jazzy-diagnostic-updater ros-jazzy-diagnostic-msgs ros-jazzy-statistics-msgs ros-jazzy-xacro ros-jazzy-backward-ros
mkdir -p "$workspace/src"
source_dir="$workspace/src/OrbbecSDK_ROS2"
if [[ ! -e "$source_dir" ]]; then git clone --branch v2-main https://github.com/orbbec/OrbbecSDK_ROS2.git "$source_dir"; fi
[[ -z "$(git -C "$source_dir" status --porcelain)" ]] || { echo 'Driver tem alterações locais; preservado'; exit 1; }
git -C "$source_dir" checkout --detach "$revision"
git -C "$source_dir" submodule update --init --recursive
source /opt/ros/jazzy/setup.bash
cd "$workspace"
export CMAKE_BUILD_PARALLEL_LEVEL=1 MAKEFLAGS=-j1
colcon build --executor sequential --cmake-args -DCMAKE_BUILD_TYPE=Release '-DCMAKE_CXX_FLAGS_RELEASE=-O1 -DNDEBUG'
source "$workspace/install/setup.bash"
ros2 pkg prefix orbbec_camera
sudo bash "$source_dir/orbbec_camera/scripts/install_udev_rules.sh"
sudo python3 - "$workspace/install/setup.bash" <<'PY'
import re,sys
from pathlib import Path
p=Path('/etc/onigiri/admin.env');s=p.read_text() if p.exists() else ''
for key,value in {'ONIGIRI_ORBBEC_SETUP':sys.argv[1],'ONIGIRI_CAMERA_DRIVER_ENABLED':'1','ONIGIRI_CAMERA_PREVIEW_ENABLED':'1'}.items():
 s=re.sub(r'^'+key+r'=.*$',key+'='+value,s,flags=re.M) if re.search(r'^'+key+'=',s,re.M) else s+'\n'+key+'='+value+'\n'
p.write_text(s)
PY
sudo systemctl restart onigiri-admin-web.service
echo 'Driver instalado. Reconecte a Gemini 2 e inicie a câmera pela aba Sensores.'
