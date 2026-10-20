"""Flush visual SLAM through its service before storing a portable snapshot."""
import shutil,sqlite3,subprocess,sys
from pathlib import Path

def main():
    import rclpy
    from std_srvs.srv import Empty
    destination=Path(sys.argv[1]);database=Path(sys.argv[2]);backup=Path(str(database)+'.back')
    rclpy.init();node=rclpy.create_node('onigiri_rgbd_save')
    try:
        client=node.create_client(Empty,'/rtabmap/backup')
        if not client.wait_for_service(timeout_sec=5):raise RuntimeError('Serviço de salvamento visual indisponível')
        backup.unlink(missing_ok=True)
        future=client.call_async(Empty.Request());rclpy.spin_until_future_complete(node,future,timeout_sec=15)
        if not future.done() or future.exception() or not backup.is_file():raise RuntimeError('RTAB-Map não confirmou o salvamento do banco visual')
        with sqlite3.connect('file:'+str(backup)+'?mode=ro',uri=True) as connection:
            if connection.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise RuntimeError('Banco visual inconsistente')
        shutil.copyfile(backup,destination.parent/'rtabmap.db')
        subprocess.run(['ros2','run','nav2_map_server','map_saver_cli','-f',str(destination),'--fmt','pgm','--ros-args','-p','save_map_timeout:=10.0','-p','map_subscribe_transient_local:=true'],check=True,timeout=15)
    finally:
        node.destroy_node()
        if rclpy.ok():rclpy.shutdown()
if __name__=='__main__':main()
