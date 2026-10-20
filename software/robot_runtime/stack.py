#!/usr/bin/env python3
"""Measured extrinsics + LiDAR odometry + Nav2. Never starts a motor service."""
import copy,json,os,sys,tempfile,shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'admin_web/app'))
from stationary_slam import run

def nav_config(defaults,config):
    rgbd=not config.get("lidar",True) and config.get("camera")=="gemini2"
    odom_topic="/odom_rgbd" if rgbd else "/odom_rf2o"
    params=copy.deepcopy(defaults)
    # ROS distribution defaults provide all required servers/plugins; override geometry.
    for node in params.values():
        if isinstance(node,dict) and 'ros__parameters' in node:
            p=node['ros__parameters']
            for key in ('base_frame_id','robot_base_frame'):
                if key in p:p[key]='base_footprint'
            if 'odom_topic' in p:p['odom_topic']=odom_topic
            if 'enable_stamped_cmd_vel' in p:p['enable_stamped_cmd_vel']=False
    w=config['body_width_m']/2;l=config['body_length_m']/2
    for key in ('local_costmap','global_costmap'):
        p=params[key][key]['ros__parameters'];p['robot_base_frame']='base_footprint'
        p.pop('robot_radius',None);p['footprint']=str([[l,w],[l,-w],[-l,-w],[-l,w]])
    omni=config['chassis']=='mecanum'
    params['amcl']['ros__parameters']['robot_model_type']='nav2_amcl::OmniMotionModel' if omni else 'nav2_amcl::DifferentialMotionModel'
    controller=params['controller_server']['ros__parameters'];controller['min_y_velocity_threshold']=.001
    path=controller['FollowPath'];path['max_vel_x']=min(.2,config['max_track_speed_mps']);path['max_vel_y']=.15 if omni else 0.;path['min_vel_y']=-.15 if omni else 0.;path['vy_samples']=5 if omni else 1
    path['max_vel_theta']=.5;path['max_speed_xy']=.2
    smoother=params['velocity_smoother']['ros__parameters'];smoother['odom_topic']=odom_topic;smoother['max_velocity']=[.2,.15 if omni else 0.,.5];smoother['min_velocity']=[-.2,-.15 if omni else 0.,-.5]
    if rgbd:
        for key in ('local_costmap','global_costmap'):
            cost=params[key][key]['ros__parameters'];cost['plugins']=['static_layer','obstacle_layer','inflation_layer']
            cost['obstacle_layer']={'plugin':'nav2_costmap_2d::ObstacleLayer','enabled':True,'observation_sources':'depth','depth':{'topic':'/camera/perception/points','data_type':'PointCloud2','sensor_frame':'camera_link','marking':True,'clearing':True,'min_obstacle_height':.05,'max_obstacle_height':1.5,'obstacle_max_range':3.,'obstacle_min_range':.15,'raytrace_max_range':5.,'raytrace_min_range':.15}}
        path.update(min_vel_x=0.,max_vel_x=.1,min_vel_y=0.,max_vel_y=0.,max_vel_theta=.2,max_speed_xy=.1,vy_samples=1)
        smoother['max_velocity']=[.1,0.,.2];smoother['min_velocity']=[0.,0.,-.2]
    return params

def tf_command(parent,child,values):
    return ['ros2','run','tf2_ros','static_transform_publisher','--x',str(values[0]),'--y',str(values[1]),'--z',str(values[2]),'--roll',str(values[3]),'--pitch',str(values[4]),'--yaw',str(values[5]),'--frame-id',parent,'--child-frame-id',child]

def main():
    import yaml
    from ament_index_python.packages import get_package_share_directory
    config=json.loads(Path(os.environ.get('ONIGIRI_PLATFORM_FILE','/home/onigiri/onigiri/data/platform.json')).read_text())
    if not config.get('extrinsics_measured'):raise SystemExit('Meça e confirme extrínsecas no painel')
    rgbd=not config.get('lidar',True) and config.get('camera')=='gemini2'
    if not config.get('lidar',True) and not rgbd:raise SystemExit('Selecione LiDAR ou Gemini 2')
    if config['chassis'] not in ('tank','mecanum'):raise SystemExit('Selecione Tank ou Mecanum; Onigiri mantém a configuração ROS original')
    map_path=Path(sys.argv[2]).resolve()
    if not map_path.is_file():raise SystemExit('Mapa ausente')
    with tempfile.TemporaryDirectory(prefix='onigiri-nav2-') as temporary:
        default=Path(get_package_share_directory('nav2_bringup'))/'params/nav2_params.yaml'
        params=Path(temporary)/'nav2.yaml';params.write_text(yaml.safe_dump(nav_config(yaml.safe_load(default.read_text()),config)))
        if rgbd:
            try:from .rgbd import commands as rgbd_commands
            except ImportError:from rgbd import commands as rgbd_commands
            database=map_path.with_name('rtabmap.db')
            if not database.is_file():raise SystemExit('Este mapa não contém o banco visual para localização RGB-D')
            working=Path(temporary)/'rtabmap.db';shutil.copyfile(database,working)
            command_list=rgbd_commands(config,working,temporary,localization=True)
            command_list.append(['ros2','launch','nav2_bringup','navigation_launch.py','params_file:='+str(params),'use_sim_time:=False','autostart:=True','use_composition:=False'])
            return run(command_list=command_list)
        commands=[tf_command('base_footprint','laser',config['lidar_xyz_rpy'])]
        if config.get('camera')=='gemini2':commands.append(tf_command('base_footprint','camera_link',config['camera_xyz_rpy']))
        commands += [
          ['ros2','run','rf2o_laser_odometry','rf2o_laser_odometry_node','--ros-args','-p','laser_scan_topic:=/scan','-p','odom_topic:=/odom_rf2o','-p','publish_tf:=true','-p','base_frame_id:=base_footprint','-p','odom_frame_id:=odom','-p','init_pose_from_topic:=""','-p','freq:=10.0'],
          ['ros2','launch','nav2_bringup','bringup_launch.py','map:='+str(map_path),'params_file:='+str(params),'use_sim_time:=False','autostart:=True','use_composition:=False']]
        return run(command_list=commands)
if __name__=='__main__':raise SystemExit(main())
