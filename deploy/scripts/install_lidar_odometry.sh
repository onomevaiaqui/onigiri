#!/usr/bin/env bash
# Optional RF2O installation. Does not start odometry, SLAM or motor services.
set -euo pipefail
[[ "$(id -un)" == onigiri ]] || { echo 'Execute como onigiri.'; exit 1; }
revision=b38c68e46387b98845ecbfeb6660292f967a00d3
workspace=/home/onigiri/onigiri-odometry/rf2o-b38c68e
sudo apt-get update
sudo apt-get install -y git build-essential cmake libeigen3-dev libboost-dev python3-yaml python3-colcon-common-extensions \
  ros-jazzy-eigen3-cmake-module ros-jazzy-rclcpp ros-jazzy-tf2-geometry-msgs ros-jazzy-tf2-ros ros-jazzy-nav-msgs ros-jazzy-sensor-msgs
mkdir -p "$workspace/src"
source_dir="$workspace/src/rf2o_laser_odometry"
if [[ ! -e "$source_dir" ]]; then
  git clone --branch ros2 https://github.com/MAPIRlab/rf2o_laser_odometry.git "$source_dir"
fi
[[ -z "$(git -C "$source_dir" status --porcelain)" ]] || { echo 'Há alterações locais no RF2O; instalação interrompida sem sobrescrever.'; exit 1; }
git -C "$source_dir" cat-file -e "$revision^{commit}"
git -C "$source_dir" checkout --detach "$revision"
cd "$workspace"
set +u
source /opt/ros/jazzy/setup.bash
set -u
export CMAKE_BUILD_PARALLEL_LEVEL=1
export MAKEFLAGS=-j1
colcon build --packages-select rf2o_laser_odometry --executor sequential --cmake-args -DCMAKE_BUILD_TYPE=Release '-DCMAKE_CXX_FLAGS_RELEASE=-O1 -DNDEBUG'
test -x "$workspace/install/rf2o_laser_odometry/lib/rf2o_laser_odometry/rf2o_laser_odometry_node"
sudo python3 -c 'from pathlib import Path; import re,sys; p=Path("/etc/onigiri/admin.env"); s=p.read_text(); values={"ONIGIRI_LIDAR_ODOMETRY_ENABLED":"1","ONIGIRI_ODOMETRY_SETUP":sys.argv[1]};
for key,value in values.items():
 s=re.sub(r"^"+key+r"=.*$",key+"="+value,s,flags=re.M) if re.search(r"^"+key+r"=",s,re.M) else s+"\n"+key+"="+value+"\n"
p.write_text(s)' "$workspace/install/setup.bash"
sudo systemctl restart onigiri-admin-web.service
echo 'RF2O instalado. No painel, encerre Teste parado e selecione Odometria pelo LiDAR.'
echo 'Nenhum serviço de motores foi iniciado. A validação física ainda é necessária.'
