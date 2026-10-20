#!/usr/bin/env python3
"""Minimal pinned RF2O startup fix: retry instead of using an absent sensor TF."""
import subprocess,sys
from pathlib import Path
revision='b38c68e46387b98845ecbfeb6660292f967a00d3'
relative='src/CLaserOdometry2DNode.cpp'
source=Path(sys.argv[1]);path=source/relative
original=subprocess.check_output(['git','-C',str(source),'show',revision+':'+relative],text=True)
patched=original.replace('      setLaserPoseFromTf();','      if (!setLaserPoseFromTf()) return;').replace('    retrieved = false;','    return false;')
if patched==original:raise SystemExit('Código upstream inesperado')
status=subprocess.check_output(['git','-C',str(source),'status','--porcelain'],text=True).splitlines()
if any(line!=' M '+relative for line in status) or path.read_text() not in (original,patched):raise SystemExit('Alterações RF2O não reconhecidas; arquivos preservados')
path.write_text(patched)
print('RF2O: inicialização aguarda TF medida')
