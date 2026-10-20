#!/usr/bin/env python3
"""Offline restore / online SQLite backup. Never includes system credentials."""
import argparse,json,os,shutil,sqlite3,tarfile,tempfile,time
from pathlib import Path

def backup(root,output):
    root=Path(root).resolve();output=Path(output)
    if output.exists():raise ValueError('Arquivo de destino já existe')
    with tempfile.TemporaryDirectory(prefix='onigiri-backup-') as temporary:
        stage=Path(temporary)
        for relative in ('data/platform.json','config/destinations.runtime.json'):
            source=root/relative
            if source.is_file():
                target=stage/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
        for source in (root/'data').glob('*.db'):
            target=stage/'data'/source.name;target.parent.mkdir(parents=True,exist_ok=True)
            with sqlite3.connect('file:'+str(source)+'?mode=ro',uri=True) as src,sqlite3.connect(target) as dst:src.backup(dst)
        if (root/'data/maps').is_dir():shutil.copytree(root/'data/maps',stage/'data/maps',ignore=shutil.ignore_patterns('.*','*.log'))
        (stage/'backup-format.json').write_text(json.dumps({'format':'onigiri-user-data','version':1,'created_at':time.time()}))
        with tarfile.open(output,'x:gz') as archive:
            for item in stage.iterdir():archive.add(item,arcname=item.name)
        output.chmod(0o600)

def restore(root,archive_path):
    root=Path(root).resolve()
    # Caller must stop the panel and base first; never merges a running SQLite DB.
    with tempfile.TemporaryDirectory(prefix='onigiri-restore-') as temporary:
        stage=Path(temporary)
        with tarfile.open(archive_path) as archive:
            total=0
            for entry in archive.getmembers():
                path=Path(entry.name);total+=entry.size
                if entry.issym() or entry.islnk() or not (entry.isfile() or entry.isdir()) or path.is_absolute() or '..' in path.parts or not path.parts or path.parts[0] not in ('data','config','backup-format.json') or total>2_000_000_000:raise ValueError('Backup inválido')
            archive.extractall(stage,filter='data')
        manifest=json.loads((stage/'backup-format.json').read_text())
        if manifest.get('format')!='onigiri-user-data' or manifest.get('version')!=1:raise ValueError('Formato de backup desconhecido')
        backup(root,root/('before-restore-'+str(time.time_ns())+'.tar.gz'))
        for folder in ('data','config'):
            for source in (stage/folder).rglob('*') if (stage/folder).exists() else []:
                if source.is_file():
                    target=root/source.relative_to(stage);target.parent.mkdir(parents=True,exist_ok=True)
                    if target.is_symlink() or not target.resolve().is_relative_to(root):raise ValueError('Destino contém link simbólico')
                    if source.suffix=='.db':
                        for suffix in ('-wal','-shm'):Path(str(target)+suffix).unlink(missing_ok=True)
                    temp=target.with_name('.'+target.name+'.restore');shutil.copyfile(source,temp);os.replace(temp,target)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('operation',choices=['backup','restore']);parser.add_argument('archive',type=Path);parser.add_argument('--root',type=Path,default=Path('/home/onigiri/onigiri'));args=parser.parse_args()
    if args.operation=='restore':
        import subprocess
        for service in ('onigiri-base','onigiri-admin-web','onigiri-udp'):
            if subprocess.run(['systemctl','is-active','--quiet',service]).returncode==0:raise SystemExit('Pare os serviços antes de restaurar')
        restore(args.root,args.archive)
    else:backup(args.root,args.archive)
if __name__=='__main__':main()
