#!/usr/bin/env bash
# Install services without enabling motor output or modifying existing Onigiri motor service.
set -euo pipefail
root="$(cd -- "$(dirname -- "$0")/../.." && pwd)"
sudo apt-get update
sudo apt-get install -y ros-jazzy-nav2-bringup ros-jazzy-navigation2 ros-jazzy-slam-toolbox ros-jazzy-tf2-ros python3-yaml python3-smbus avahi-daemon
sudo groupadd -f i2c
sudo usermod -aG dialout,i2c onigiri
sudo install -d -m 755 /etc/onigiri
sudo install -m 644 "$root/deploy/systemd/onigiri-udp.service" /etc/systemd/system/onigiri-udp.service
sudo install -m 644 "$root/deploy/systemd/onigiri-base.service" /etc/systemd/system/onigiri-base.service
sudo python3 - <<'PY'
from pathlib import Path
import re
p=Path('/etc/onigiri/admin.env');s=p.read_text() if p.exists() else ''
for key in ('ONIGIRI_RUNTIME_ENABLED','ONIGIRI_MAPPING_ENABLED'):
 s=re.sub(r'^'+key+r'=.*$',key+'=1',s,flags=re.M) if re.search(r'^'+key+'=',s,re.M) else s+'\n'+key+'=1\n'
if not re.search(r'^ONIGIRI_MOTION_ENABLED=',s,re.M):s+='ONIGIRI_MOTION_ENABLED=0\n'
p.write_text(s)
PY
sudo systemctl daemon-reload
sudo systemctl restart onigiri-admin-web.service
echo 'Runtime instalado. Serviço da base não foi habilitado; movimento permanece conforme configuração existente.'
