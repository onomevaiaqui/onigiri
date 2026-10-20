"""Experimental sensor-frame mapping with RF2O; never publishes motion commands."""
import copy
import tempfile
from pathlib import Path


def configure_slam(defaults):
    config = copy.deepcopy(defaults)
    params = config['slam_toolbox']['ros__parameters']
    params.update(base_frame='laser', odom_frame='odom', map_frame='map', scan_topic='/scan',
                  use_sim_time=False, minimum_travel_distance=0.05, minimum_travel_heading=0.05,
                  minimum_time_interval=0.1, map_update_interval=1.0)
    return config


def commands(params_file):
    return [
        ['ros2', 'run', 'rf2o_laser_odometry', 'rf2o_laser_odometry_node', '--ros-args',
         '-p', 'laser_scan_topic:=/scan', '-p', 'odom_topic:=/odom_rf2o',
         '-p', 'publish_tf:=true', '-p', 'base_frame_id:=laser', '-p', 'odom_frame_id:=odom',
         '-p', 'init_pose_from_topic:=""', '-p', 'freq:=10.0'],
        ['ros2', 'launch', 'slam_toolbox', 'online_async_launch.py', 'use_sim_time:=false',
         'slam_params_file:=' + str(params_file)]
    ]


def main():
    import yaml
    from ament_index_python.packages import get_package_share_directory
    try:
        from .stationary_slam import run
    except ImportError:
        from stationary_slam import run
    # Fail before starting SLAM if the optional odometry dependency is absent.
    get_package_share_directory('rf2o_laser_odometry')
    default = Path(get_package_share_directory('slam_toolbox')) / 'config/mapper_params_online_async.yaml'
    with tempfile.TemporaryDirectory(prefix='onigiri-lidar-odom-') as temporary:
        params = Path(temporary) / 'slam.yaml'
        params.write_text(yaml.safe_dump(configure_slam(yaml.safe_load(default.read_text()))))
        return run(command_list=commands(params))


if __name__ == '__main__':
    raise SystemExit(main())
