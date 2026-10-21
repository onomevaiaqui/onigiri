#!/usr/bin/env bash
# Installs only the admin panel update. Run as the operational user on the Pi.
set -euo pipefail
bundle_root="$(cd -- "${1:-$(dirname -- "$0")}" && pwd)"
project_root=/home/onigiri/onigiri
if [[ "$(id -un)" != onigiri ]]; then echo 'Execute como usuário onigiri.'; exit 1; fi
test -f /opt/ros/jazzy/setup.bash || { echo 'ROS Jazzy não encontrado.'; exit 1; }
cd "$bundle_root"
sha256sum --check --quiet SHA256SUMS
if [[ ! -d "$project_root" ]]; then
  echo 'Primeira instalação: criando /home/onigiri/onigiri para o painel.'
  mkdir -p "$project_root"
fi
echo 'Arquivos verificados. Preparando dependências do painel…'
if ! python3 -c 'import ensurepip' >/dev/null 2>&1; then
  echo 'Instalando suporte a ambientes virtuais Python…'
  sudo apt-get update
  sudo apt-get install -y python3-venv
fi
python3 -m venv "$project_root/.venv-admin"
"$project_root/.venv-admin/bin/python" -m pip install -r payload/software/admin_web/requirements.txt
backup_root="$(mktemp -d /home/onigiri/onigiri-panel-backup-XXXXXXXX)"
mkdir -p "$backup_root/files"
while IFS= read -r relative_path; do
  if [[ -f "$project_root/$relative_path" ]]; then
    if ! cmp -s "$project_root/$relative_path" "payload/$relative_path"; then echo "Atualizando: $relative_path"; fi
    mkdir -p "$backup_root/files/$(dirname "$relative_path")"
    cp -a "$project_root/$relative_path" "$backup_root/files/$relative_path"
  else
    echo "$relative_path" >> "$backup_root/new-files.txt"
  fi
done < FILES
sudo install -d -m 755 /etc/onigiri
if [[ -f /etc/onigiri/admin.env ]]; then sudo cp -a /etc/onigiri/admin.env "$backup_root/admin.env"; fi
if [[ -f /etc/systemd/system/onigiri-admin-web.service ]]; then sudo cp -a /etc/systemd/system/onigiri-admin-web.service "$backup_root/onigiri-admin-web.service"; fi
echo "Backup dos arquivos anteriores: $backup_root"
rollback() {
  trap - ERR
  echo "Falha na atualização; restaurando arquivos gerenciados de $backup_root"
  cp -a "$backup_root/files/." "$project_root/"
  if [[ -d "$backup_root/retired-platforms" ]]; then cp -a "$backup_root/retired-platforms/." "$project_root/"; fi
  if [[ -f "$backup_root/new-files.txt" ]]; then
    while IFS= read -r relative_path; do rm -f -- "$project_root/$relative_path"; done < "$backup_root/new-files.txt"
  fi
  if [[ -f "$backup_root/admin.env" ]]; then sudo cp -a "$backup_root/admin.env" /etc/onigiri/admin.env; fi
  if [[ -f "$backup_root/onigiri-admin-web.service" ]]; then sudo cp -a "$backup_root/onigiri-admin-web.service" /etc/systemd/system/onigiri-admin-web.service; fi
  sudo systemctl daemon-reload
  sudo systemctl restart onigiri-admin-web.service || true
  exit 1
}
trap rollback ERR
if systemctl is-active --quiet onigiri-base.service; then
  echo 'Encerrando o antigo serviço de base genérico para dedicar este sistema ao Onigiri.'
  sudo systemctl stop onigiri-base.service
fi
# The generic base belongs to Omni Framework, never the dedicated Onigiri panel.
sudo systemctl disable --now onigiri-base.service 2>/dev/null || true
python3 payload/deploy/scripts/retire_platform_files.py "$project_root" "$backup_root"
while IFS= read -r relative_path; do
  mkdir -p "$project_root/$(dirname "$relative_path")"
  cp "payload/$relative_path" "$project_root/$relative_path"
done < FILES
mkdir -p "$project_root/data/maps"
if [[ ! -e /etc/onigiri/admin.env ]]; then
  sudo install -m 640 -o root -g onigiri "$project_root/config/admin.env.example" /etc/onigiri/admin.env
fi
# Enable ROS capture; starting the SLAM still requires an explicit button click.
sudo python3 -c 'from pathlib import Path; import re; p=Path("/etc/onigiri/admin.env"); s=p.read_text(); s=re.sub(r"^ONIGIRI_MAPPING_ENABLED=.*$", "ONIGIRI_MAPPING_ENABLED=1", s, flags=re.M) if re.search(r"^ONIGIRI_MAPPING_ENABLED=",s,re.M) else s+"\nONIGIRI_MAPPING_ENABLED=1\n"; p.write_text(s)'
sudo install -m 644 "$project_root/deploy/systemd/onigiri-admin-web.service" /etc/systemd/system/onigiri-admin-web.service
sudo systemctl daemon-reload
sudo systemctl enable onigiri-admin-web.service
sudo systemctl restart onigiri-admin-web.service
for attempt in {1..30}; do
  if curl -fsS http://127.0.0.1:8080/api/health >/dev/null; then
    echo 'Painel atualizado e respondendo. Nenhum serviço de motores foi reiniciado.'
    echo
    trap - ERR
    exit 0
  fi
  sleep 1
done
echo 'O painel não respondeu. Diagnóstico: sudo journalctl -u onigiri-admin-web -n 60 --no-pager'
echo "Backup: $backup_root"
rollback
