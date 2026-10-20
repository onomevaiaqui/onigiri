#!/usr/bin/env bash
# Optional headless visual mapping packages. Never starts motors.
set -euo pipefail
sudo apt-get update
sudo apt-get install -y ros-jazzy-rtabmap-sync ros-jazzy-rtabmap-odom ros-jazzy-rtabmap-slam ros-jazzy-rtabmap-util
sudo install -d -m 755 /etc/onigiri
sudo python3 - <<'PY'
import re
from pathlib import Path
p=Path('/etc/onigiri/admin.env');s=p.read_text() if p.exists() else ''
for key in ('ONIGIRI_RGBD_ENABLED','ONIGIRI_MAPPING_ENABLED'):
 s=re.sub(r'^'+key+r'=.*$',key+'=1',s,flags=re.M) if re.search(r'^'+key+'=',s,re.M) else s+'\n'+key+'=1\n'
p.write_text(s)
PY
sudo systemctl restart onigiri-admin-web.service
echo 'RGB-D instalado. Selecione Gemini 2, desmarque LiDAR e configure a câmera no perfil.'
