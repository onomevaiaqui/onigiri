#!/usr/bin/env bash
# Explicit network setup installation; does not modify motor services.
set -euo pipefail
root="$(cd -- "$(dirname -- "$0")/../.." && pwd)"
[[ "$(id -u)" == 0 ]] || { echo 'Execute com sudo'; exit 1; }
if [[ "${ONIGIRI_OFFLINE_PREPARE:-0}" != 1 ]]; then
 apt-get update
 apt-get install -y network-manager dnsmasq-base avahi-daemon
fi
install -d -m 755 /etc/onigiri /opt/onigiri-network /etc/NetworkManager/system-connections /etc/netplan
install -m 644 "$root/deploy/scripts/network_agent.py" "$root/deploy/scripts/first_access.html" /opt/onigiri-network/
python3 - <<'PYCONFIG'
import json,secrets,uuid,os
from pathlib import Path
p=Path('/etc/onigiri/access.json')
if not p.exists():
 p.write_text(json.dumps({'ssid':'Onigiri-Config-'+secrets.token_hex(3).upper(),'password':secrets.token_urlsafe(12),'interface':'wlan0'}))
config=json.loads(p.read_text());os.chmod(p,0o640)
import grp
os.chown(p,0,grp.getgrnam('onigiri').gr_gid)
profile=Path('/etc/NetworkManager/system-connections/onigiri-setup.nmconnection')
if not profile.exists():
 profile.write_text(f'[connection]\nid=onigiri-setup\nuuid={uuid.uuid4()}\ntype=wifi\ninterface-name=wlan0\nautoconnect=true\nautoconnect-priority=-999\n[wifi]\nmode=ap\nband=bg\nssid={config["ssid"]}\n[wifi-security]\nkey-mgmt=wpa-psk\npsk={config["password"]}\n[ipv4]\nmethod=shared\naddress1=192.168.50.1/24\n[ipv6]\nmethod=disabled\n')
 os.chmod(profile,0o600)
netplan=Path('/etc/netplan/90-onigiri-wifi.yaml');netplan.write_text('network:\n  version: 2\n  renderer: NetworkManager\n');os.chmod(netplan,0o600)
PYCONFIG
install -m 644 "$root/deploy/systemd/onigiri-network.service" "$root/deploy/systemd/onigiri-first-access.service" /etc/systemd/system/
mkdir -p /etc/systemd/system/onigiri-admin-web.service.d
cat > /etc/systemd/system/onigiri-admin-web.service.d/network.conf <<'UNIT'
[Unit]
Conflicts=onigiri-first-access.service
[Service]
ExecStart=
ExecStart=/home/onigiri/onigiri/.venv-admin/bin/python -m uvicorn app.main:app --app-dir software/admin_web --host 0.0.0.0 --port 8080
UNIT
netplan generate
systemctl enable NetworkManager.service avahi-daemon.service onigiri-network.service
if [[ "${ONIGIRI_OFFLINE_PREPARE:-0}" != 1 ]]; then
 systemctl daemon-reload
 systemctl start NetworkManager.service avahi-daemon.service onigiri-network.service
 nmcli connection reload
 systemctl restart onigiri-admin-web.service
 echo 'Rede instalada. Credenciais locais em /etc/onigiri/access.json. Wi-Fi gerenciado pelo NetworkManager após reiniciar.'
fi
