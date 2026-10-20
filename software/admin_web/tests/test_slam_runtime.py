import unittest
from app.slam_runtime import configure_preview


class SlamRuntimeTests(unittest.TestCase):
    def test_publication_interval_changes_without_changing_calibration(self):
        original={'slam_toolbox':{'ros__parameters':{'map_update_interval':5.,'base_frame':'robot','resolution':.05}}}
        result=configure_preview(original)['slam_toolbox']['ros__parameters']
        self.assertEqual(result['map_update_interval'],1.)
        self.assertEqual(result['base_frame'],'robot')
        self.assertEqual(result['resolution'],.05)
        self.assertEqual(original['slam_toolbox']['ros__parameters']['map_update_interval'],5.)
