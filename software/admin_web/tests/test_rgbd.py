import json,os,struct,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from robot_runtime.rgbd import source,configurations,commands
from robot_runtime.depth_guard import assess
from robot_runtime.stack import nav_config
from app.mapping import MapManager

class RGBDTests(unittest.TestCase):
    def test_profile_selects_sensor_without_requiring_lidar(self):
        self.assertEqual(source({'lidar':False,'camera':'gemini2'}),'rgbd')
        self.assertEqual(source({'lidar':True,'camera':'gemini2'}),'lidar')
        with self.assertRaises(ValueError):source({'lidar':False,'camera':'none'})
    def test_commands_share_one_synchronized_stream_and_keep_database(self):
        with tempfile.TemporaryDirectory() as folder:
            config={'camera_xyz_rpy':[.2,0,.4,0,0,0]}
            result=commands(config,Path(folder)/'rtabmap.db',folder)
            flat=' '.join(' '.join(cmd) for cmd in result)
            self.assertNotIn('rf2o',flat);self.assertNotIn('slam_toolbox',flat)
            self.assertEqual(flat.count('rgbd_image:=/onigiri/rgbd'),3)
            self.assertIn('depth_guard.py',flat)
            self.assertEqual(configurations('x',True)['rtabmap']['Mem/IncrementalMemory'],'false')
            self.assertEqual(configurations('x')['rtabmap']['qos_odom'],2)
    def test_rgbd_launch_requires_install_and_rejects_fake_tf_modes(self):
        with tempfile.TemporaryDirectory() as folder:
            manager=MapManager(Path(folder)/'maps',Path(folder)/'worker',True)
            with patch('app.mapping.subprocess.Popen') as process:
                with self.assertRaises(ValueError):manager.start(rgbd=True)
                manager.rgbd_enabled=True
                with self.assertRaises(ValueError):manager.start(rgbd=True,stationary=True)
                process.assert_not_called()
    def test_depth_clearance_invalid_and_floor(self):
        k=[100.,0.,1.,0.,100.,1.,0.,0.,1.];rotation=[[0,0,1],[-1,0,0],[0,-1,0]]
        def check(value,height=.4):return assess(4,4,8,'16UC1',struct.pack('<16H',*[value]*16),k,rotation,[0,0,height],.5)[0]
        self.assertTrue(check(2000)['clear']);self.assertFalse(check(200)['clear']);self.assertFalse(check(0)['clear'])
        self.assertTrue(check(200,-1)['clear']) # observed points below floor do not mark obstacles
    def test_visual_nav_uses_depth_cloud_and_visual_odometry(self):
        import yaml
        path=Path('/opt/ros/jazzy/share/nav2_bringup/params/nav2_params.yaml')
        if not path.exists():self.skipTest('Nav2 não instalado')
        c={'chassis':'tank','camera':'gemini2','lidar':False,'body_width_m':.4,'body_length_m':.4,'max_track_speed_mps':.3}
        params=nav_config(yaml.safe_load(path.read_text()),c)
        self.assertEqual(params['bt_navigator']['ros__parameters']['odom_topic'],'/odom_rgbd')
        self.assertEqual(params['local_costmap']['local_costmap']['ros__parameters']['obstacle_layer']['depth']['data_type'],'PointCloud2')
        self.assertEqual(params['controller_server']['ros__parameters']['FollowPath']['min_vel_x'],0.)
