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
sudo install -m 644 deploy/systemd/onigiri-mission.service /etc/systemd/system/onigiri-mission.service
sudo install -d -m 755 /etc/onigiri
if [[ ! -e /etc/onigiri/admin.env ]]; then
  sudo install -m 640 -o root -g onigiri config/admin.env.example /etc/onigiri/admin.env
fi
mkdir -p "$project_root/data/maps"
sudo systemctl daemon-reload
sudo systemctl enable --now onigiri-admin-web.service
if [[ -e /etc/systemd/system/onigiri-admin-web.service.d/network.conf ]]; then
 echo "Painel disponível na rede na porta 8080, com autenticação do cartão de acesso."
else
 echo "Painel instalado apenas em 127.0.0.1:8080. Acesse por tunel SSH a partir do PC."
fi
echo "O arquivo do servico de missoes foi atualizado; reinicie-o de forma controlada para usar a configuracao exportada."
