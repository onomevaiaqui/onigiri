"""RGB-D capture/localization using one synchronized camera stream. No motor startup."""
import json,os,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'admin_web/app'))
from stationary_slam import run

def source(config):
    if config.get('lidar',True):return 'lidar'
    if config.get('camera')=='gemini2':return 'rgbd'
    raise ValueError('Selecione LiDAR ou uma Gemini 2 para mapear')

def topics():
    return {'rgb':os.environ.get('ONIGIRI_CAMERA_COLOR_TOPIC','/camera/color/image_raw'),
            'depth':os.environ.get('ONIGIRI_CAMERA_DEPTH_TOPIC','/camera/depth/image_raw'),
            'info':os.environ.get('ONIGIRI_CAMERA_INFO_TOPIC','/camera/color/camera_info')}

def configurations(database,localization=False):
    return {
      'rgbd_sync':{'approx_sync':True,'approx_sync_max_interval':.03,'qos':2,'qos_camera_info':2,'topic_queue_size':5,'sync_queue_size':5},
      'rgbd_odometry':{'subscribe_rgbd':True,'frame_id':'base_footprint','odom_frame_id':'odom','publish_tf':True,'qos':2,'max_update_rate':5.,'Odom/ImageDecimation':'2','Vis/MaxFeatures':'600','Reg/Force3DoF':'true'},
      'rtabmap':{'subscribe_depth':False,'subscribe_rgb':False,'subscribe_rgbd':True,'frame_id':'base_footprint','map_frame_id':'map','publish_tf':True,'qos_image':2,'qos_odom':2,'approx_sync':False,'approx_sync_max_interval':.1,'database_path':str(database),'Mem/IncrementalMemory':'false' if localization else 'true','Mem/InitWMWithAllNodes':'true' if localization else 'false','Reg/Force3DoF':'true','Rtabmap/DetectionRate':'1.0','Grid/FromDepth':'true','Grid/RangeMax':'3.0','Grid/CellSize':'0.05','Grid/DepthDecimation':'4','Grid/MaxGroundHeight':'0.08','Grid/MaxObstacleHeight':'1.5','Grid/RayTracing':'true','RGBD/LinearUpdate':'0.05','RGBD/AngularUpdate':'0.05'}
    }

def commands(config,database,directory,localization=False):
    import yaml
    try:from .stack import tf_command
    except ImportError:from stack import tf_command
    t=topics();directory=Path(directory);result=[tf_command('base_footprint','camera_link',config['camera_xyz_rpy'])]
    remaps={
       'rgbd_sync':[('rgb/image',t['rgb']),('depth/image',t['depth']),('rgb/camera_info',t['info']),('rgbd_image','/onigiri/rgbd')],
       'rgbd_odometry':[('rgbd_image','/onigiri/rgbd'),('odom','/odom_rgbd')],
       'rtabmap':[('rgbd_image','/onigiri/rgbd'),('odom','/odom_rgbd'),('map','/map')]}
    packages={'rgbd_sync':'rtabmap_sync','rgbd_odometry':'rtabmap_odom','rtabmap':'rtabmap_slam'}
    for name,params in configurations(database,localization).items():
        path=directory/(name+'.yaml');path.write_text(yaml.safe_dump({name:{'ros__parameters':params}}))
        command=['ros2','run',packages[name],name,'--ros-args','--params-file',str(path)]
        for key,value in remaps[name]:command+=['-r',key+':='+value]
        result.append(command)
    result.append(["/usr/bin/python3",str(Path(__file__).with_name("depth_guard.py"))])
    return result

def main():
    from ament_index_python.packages import get_package_share_directory
    root=Path(__file__).resolve().parents[2]
    config=json.loads(Path(os.environ.get('ONIGIRI_PLATFORM_FILE',root/'data/platform.json')).read_text())
    if source(config)!='rgbd':raise SystemExit('Selecione Gemini 2 e desmarque LiDAR no painel')
    if not config.get('extrinsics_measured'):raise SystemExit('Configure e confirme a posição medida da câmera na base')
    for package in ('rtabmap_sync','rtabmap_odom','rtabmap_slam'):get_package_share_directory(package)
    with tempfile.TemporaryDirectory(prefix='onigiri-rgbd-') as directory:
        return run(command_list=commands(config,sys.argv[1],directory))
if __name__=='__main__':raise SystemExit(main())
