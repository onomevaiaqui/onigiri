"""Temporary SLAM configuration with a bounded map publication interval."""
import copy
import tempfile
from contextlib import contextmanager
from pathlib import Path


def configure_preview(defaults):
    config=copy.deepcopy(defaults)
    config['slam_toolbox']['ros__parameters']['map_update_interval']=1.0
    return config


@contextmanager
def parameters(source=None):
    import yaml
    from ament_index_python.packages import get_package_share_directory
    source=Path(source) if source else Path(get_package_share_directory('slam_toolbox'))/'config/mapper_params_online_async.yaml'
    with tempfile.TemporaryDirectory(prefix='onigiri-slam-preview-') as temporary:
        path=Path(temporary)/'slam.yaml'
        path.write_text(yaml.safe_dump(configure_preview(yaml.safe_load(source.read_text()))))
        yield path


if __name__=='__main__':
    import sys
    from stationary_slam import run
    with parameters(sys.argv[1] if len(sys.argv)>1 else None) as path:
        raise SystemExit(run(command_list=[['ros2','launch','slam_toolbox','online_async_launch.py',
                                           'use_sim_time:=false','slam_params_file:='+str(path)]]))
