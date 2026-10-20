#!/usr/bin/env python3
"""Customize a COPY of an Ubuntu preinstalled Raspberry Pi image. Never flashes disks."""
import argparse,base64,hashlib,json,lzma,os,shutil,subprocess,tempfile
from pathlib import Path

def cloud_config(public_key):
    if not public_key.startswith(('ssh-ed25519 ','ssh-rsa ','ecdsa-sha2-')) or '\n' in public_key.strip():raise ValueError('Chave pública SSH inválida')
    return {'groups':['i2c'],'hostname':'onigiri','manage_etc_hosts':True,'ssh_pwauth':False,
      'users':[{'name':'onigiri','groups':['adm','sudo','dialout','i2c'],'shell':'/bin/bash','lock_passwd':True,'sudo':'ALL=(ALL) NOPASSWD:ALL','ssh_authorized_keys':[public_key.strip()]}],
      'runcmd':[['mkdir','-p','/opt/onigiri-bootstrap'],['tar','-xzf','/boot/firmware/onigiri-bundle.tar.gz','-C','/opt/onigiri-bootstrap'],['bash','/opt/onigiri-bootstrap/payload/deploy/scripts/provision_image.sh']]}

def main():
    import yaml,tarfile
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',required=True,type=Path);parser.add_argument('--sha256',required=True)
    parser.add_argument('--public-key',required=True,type=Path);parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--model',choices=['raspberry4','raspberry5'],required=True)
    parser.add_argument('--with-orbbec',action='store_true')
    args=parser.parse_args()
    if os.geteuid()!=0:parser.error('Execute com sudo; mount/losetup necessários')
    source=args.base.resolve();output=args.output.resolve()
    if output.exists() or output.suffix!='.img' or source==output:parser.error('Destino deve ser arquivo .img novo')
    if not output.parent.is_dir():parser.error('Pasta de destino inexistente')
    digest=hashlib.sha256()
    with source.open('rb') as stream:
        for chunk in iter(lambda:stream.read(4*1024*1024),b''):digest.update(chunk)
    if digest.hexdigest()!=args.sha256.lower():parser.error('SHA256 do Ubuntu não confere')
    public=args.public_key.read_text().strip();seed=cloud_config(public)
    root=Path(__file__).resolve().parents[2];loop=None
    with tempfile.TemporaryDirectory(prefix='onigiri-image-') as temporary:
        stage=Path(temporary);payload=stage/'bundle';payload.mkdir()
        with tarfile.open(stage/'onigiri-bundle.tar.gz','w:gz') as archive:
            for folder in ('software','config','deploy','docs'):
                for path in sorted((root/folder).rglob('*')):
                    if path.is_file() and '__pycache__' not in path.parts and not path.name.endswith(('.runtime.json','.pyc')) and path.name!='destinations.json':
                        archive.add(path,arcname='payload/'+str(path.relative_to(root)),recursive=False)
            profile=payload/'platform.json';profile.write_text(json.dumps({'computer':args.model,'chassis':'onigiri','motor_driver':'onigiri_hat','camera':'gemini2' if args.with_orbbec else 'none','lidar':True,'track_separation_m':.3}))
            archive.add(profile,arcname='platform.json')
            if args.with_orbbec:
                marker=payload/'with-orbbec';marker.touch();archive.add(marker,arcname='with-orbbec')
        opener=lzma.open if source.suffix=='.xz' else open
        with opener(source,'rb') as src,output.open('xb') as dst:shutil.copyfileobj(src,dst,4*1024*1024)
        mount=stage/'boot';mount.mkdir();mounted=False
        try:
            loop=subprocess.check_output(['losetup','--find','--show','--partscan',str(output)],text=True).strip()
            subprocess.run(['udevadm','settle'],check=True)
            subprocess.run(['mount',loop+'p1',str(mount)],check=True);mounted=True
            if not (mount/'config.txt').exists():raise ValueError('Partição de boot Raspberry Pi não reconhecida')
            (mount/'user-data').write_text('#cloud-config\n'+yaml.safe_dump(seed,sort_keys=False))
            (mount/'meta-data').write_text('instance-id: onigiri-'+hashlib.sha256(public.encode()).hexdigest()[:12]+'\nlocal-hostname: onigiri\n')
            (mount/'network-config').write_text(yaml.safe_dump({'version':2,'ethernets':{'ethernet':{'match':{'name':'e*'},'dhcp4':True,'optional':True}}}))
            shutil.copyfile(stage/'onigiri-bundle.tar.gz',mount/'onigiri-bundle.tar.gz')
            os.sync()
        finally:
            if mounted:subprocess.run(['umount',str(mount)],check=True)
            if loop:subprocess.run(['losetup','-d',loop],check=True)
    print('Imagem preparada:',output)
    print('Primeiro boot exige Ethernet com Internet para instalar ROS e dependências. Movimento desabilitado.')
if __name__=='__main__':main()
