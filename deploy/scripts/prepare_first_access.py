#!/usr/bin/env python3
"""Prepare first-access services in a mounted ARM64 image root, never a live disk."""
import argparse,json,os,shutil,subprocess
from pathlib import Path

def prepare(root,source,credentials):
 if os.geteuid()!=0:raise ValueError('Execute como root')
 root=Path(root).resolve();source=Path(source).resolve()
 if root==Path('/') or not (root/'etc/os-release').is_file():raise ValueError('Raiz da imagem inválida')
 if not (root/'boot/firmware/config.txt').is_file():raise ValueError('Monte também a partição de boot da imagem')
 stage=root/'opt/onigiri-first-access-source';stage.mkdir(parents=True,exist_ok=True)
 for folder in ('deploy/scripts','deploy/systemd'):
  destination=stage/folder;destination.mkdir(parents=True,exist_ok=True)
  names=('network_agent.py','first_access.html','install_network.sh') if folder.endswith('scripts') else ('onigiri-network.service','onigiri-first-access.service')
  for name in names:shutil.copyfile(source/folder/name,destination/name)
 # qemu-user-static/binfmt must be installed on the build host.
 subprocess.run(['chroot',str(root),'/usr/bin/true'],check=True)
 resolver=root/'etc/resolv.conf';old_link=os.readlink(resolver) if resolver.is_symlink() else None;old_data=resolver.read_bytes() if resolver.exists() and not resolver.is_symlink() else None
 if resolver.is_symlink():resolver.unlink()
 resolver.write_bytes(Path('/etc/resolv.conf').read_bytes())
 policy=root/'usr/sbin/policy-rc.d';previous=policy.read_bytes() if policy.exists() else None
 policy.write_text('#!/bin/sh\nexit 101\n');policy.chmod(0o755)
 apt_config=root/'tmp/onigiri-build-apt.conf';apt_config.write_text('#clear APT::Update::Post-Invoke-Success;\n#clear DPkg::Post-Invoke;\n')
 mounts=[]
 try:
  for name in ('dev','proc','sys'):
   (root/name).mkdir(exist_ok=True)
   subprocess.run(['mount','--bind','/'+name,str(root/name)],check=True);mounts.append(root/name)
  subprocess.run(['chroot',str(root),'/bin/bash','-c','export DEBIAN_FRONTEND=noninteractive; apt-get -c /tmp/onigiri-build-apt.conf update -o APT::Update::Error-Mode=any && apt-get -c /tmp/onigiri-build-apt.conf install -y network-manager dnsmasq-base avahi-daemon curl ca-certificates && groupadd -f onigiri && ONIGIRI_OFFLINE_PREPARE=1 bash /opt/onigiri-first-access-source/deploy/scripts/install_network.sh && systemctl enable onigiri-first-access.service'],check=True)
  config=json.loads((root/'etc/onigiri/access.json').read_text())
  Path(credentials).write_text('ONIGIRI — PRIMEIRO ACESSO\n\nRede Wi-Fi: '+config['ssid']+'\nSenha do Wi-Fi: '+config['password']+'\nNavegador: http://192.168.50.1:8080\nUsuário do painel: onigiri\nSenha do painel: '+config['password']+'\n\nConecte ao Wi-Fi acima. Cadastre o Wi-Fi comum no navegador. Depois acesse http://onigiri.local:8080 ou o IP do roteador. Guarde este cartão de acesso.\n')
  Path(credentials).chmod(0o600)
  shutil.copyfile(credentials,root/'boot/firmware/ONIGIRI-ACESSO.txt')
  subprocess.run(['chroot',str(root),'apt-get','clean'],check=True)
 finally:
  apt_config.unlink(missing_ok=True)
  for mount in reversed(mounts):subprocess.run(['umount',str(mount)],check=True)
  resolver.unlink(missing_ok=True)
  if old_link:resolver.symlink_to(old_link)
  elif old_data is not None:resolver.write_bytes(old_data)
  if previous is None:policy.unlink(missing_ok=True)
  else:policy.write_bytes(previous)
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--root',required=True,type=Path);parser.add_argument('--credentials',required=True,type=Path);args=parser.parse_args();prepare(args.root,Path(__file__).resolve().parents[2],args.credentials)
