import os
import tempfile
import unittest
from pathlib import Path

from app.lidar_odometry import commands, configure_slam
from app.mapping import MapManager


class LidarOdometryTests(unittest.TestCase):
    def test_slam_tracks_sensor_without_fake_base_transform(self):
        original={'slam_toolbox':{'ros__parameters':{'base_frame':'base_footprint','resolution':.05}}}
        result=configure_slam(original)['slam_toolbox']['ros__parameters']
        self.assertEqual(original['slam_toolbox']['ros__parameters']['base_frame'],'base_footprint')
        self.assertEqual(result['base_frame'],'laser')
        self.assertEqual(result['odom_frame'],'odom')
        self.assertFalse(result['use_sim_time'])
        self.assertEqual(result['resolution'],.05)
        self.assertEqual(result['minimum_travel_distance'],.05)

    def test_only_odometry_and_slam_commands(self):
        items=commands('/tmp/params.yaml')
        self.assertEqual(len(items),2)
        self.assertIn('publish_tf:=true',items[0])
        self.assertIn('base_frame_id:=laser',items[0])
        self.assertIn('slam_params_file:=/tmp/params.yaml',items[1])
        self.assertNotIn('static_transform_publisher',' '.join(sum(items,[])))
        self.assertNotIn('cmd_vel',' '.join(sum(items,[])))

    def test_requires_dependency_enable_and_excludes_stationary(self):
        with tempfile.TemporaryDirectory() as temporary:
            manager=MapManager(Path(temporary),Path(temporary)/'worker',enabled=True)
            manager.lidar_enabled=False
            with self.assertRaises(ValueError):manager.start(lidar_odometry=True)
            manager.lidar_enabled=True
            with self.assertRaises(ValueError):manager.start(stationary=True,lidar_odometry=True)

    @unittest.skipUnless(os.name=='posix','Linux worker')
    def test_profile_lifecycle_and_saved_map_identification(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);worker=root/'worker'
            worker.write_text('''case "$1" in
start-lidar-odometry|preview) exec sleep 60 ;;
save) printf 'image: map.pgm\\nresolution: 0.05\\norigin: [0, 0, 0]\\n' > "$2.yaml"; printf 'P2\\n1 1\\n255\\n255\\n' > "$2.pgm" ;;
esac
''')
            manager=MapManager(root/'maps',worker,enabled=True);manager.lidar_enabled=True
            try:
                self.assertEqual(manager.start(lidar_odometry=True)['profile'],'lidar-odometry')
                self.assertEqual(manager.process.args[-1],'start-lidar-odometry')
                manager.save('movimento')
                self.assertEqual(manager.list()[0]['profile'],'lidar-odometry')
                self.assertEqual(manager.read('movimento')['profile'],'lidar-odometry')
            finally:manager.stop()
