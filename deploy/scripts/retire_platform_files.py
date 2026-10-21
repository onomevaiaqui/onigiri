"""Quarantine only known obsolete platform files during an Onigiri update."""
from pathlib import Path
import shutil,sys
FILES=['software/robot_runtime','software/admin_web/app/runtime.py','software/admin_web/app/sabertooth.py','software/admin_web/app/camera.py','software/admin_web/app/camera_preview_ros.py','software/admin_web/app/static/runtime.js','software/admin_web/app/static/icons/frames/tank.svg','software/admin_web/app/static/icons/frames/mecanum.svg']
FILES += ['deploy/scripts/'+name for name in ['base_worker.sh','camera_driver_worker.sh','camera_preview_worker.sh','navigation_worker.sh','robot_bridge_worker.sh','install_orbbec.sh','install_rgbd.sh','install_robot_runtime.sh','start_gemini2.sh']]
FILES += ['deploy/systemd/onigiri-base.service','docs/OPERACAO_ROBOTICA.md','docs/PLATAFORMAS_E_SENSORES.md','docs/ROBO_RGBD.md','docs/VALIDACAO_RUNTIME.md']
FILES += ['software/admin_web/tests/'+name for name in ['test_camera.py','test_rgbd.py','test_robot_runtime.py','test_sabertooth.py','rgbd_ros_integration.py','runtime_ros_integration.py','nav2_ros_integration.py','platforms.browser.cjs','robot-profile.browser.cjs','frame-icons.browser.cjs']]
def retire(root,backup):
 root=Path(root).resolve();backup=Path(backup).resolve()
 if root==backup or root in backup.parents:raise ValueError('Backup deve ficar fora do projeto')
 for name in FILES:
  source=root/name
  if source.exists() or source.is_symlink():
   if not source.resolve().is_relative_to(root):raise ValueError('Arquivo fora do projeto')
   target=backup/'retired-platforms'/name;target.parent.mkdir(parents=True,exist_ok=True)
   if target.exists():raise FileExistsError(target)
   shutil.move(str(source),str(target))
if __name__=='__main__':retire(*sys.argv[1:])
