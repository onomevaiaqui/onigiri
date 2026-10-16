#!/usr/bin/env bash
# Instala o painel local no Raspberry Pi. Execute somente após validar no PC.
set -euo pipefail

project_root="/home/onigiri/onigiri"
venv_path="$project_root/.venv-admin"

cd "$project_root"
python3 -m venv "$venv_path"
"$venv_path/bin/python" -m pip install --upgrade pip
"$venv_path/bin/python" -m pip install -r software/admin_web/requirements.txt
sudo install -m 644 deploy/systemd/onigiri-admin-web.service /etc/systemd/system/onigiri-admin-web.service
sudo systemctl daemon-reload
sudo systemctl enable --now onigiri-admin-web.service
echo "Painel instalado apenas em 127.0.0.1:8080. Acesse por tunel SSH a partir do PC."
