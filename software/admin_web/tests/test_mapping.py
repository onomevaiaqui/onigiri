import base64
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.mapping import MapManager


YAML = 'image: /old/location/map.pgm\nresolution: 0.05\norigin: [0, 0, 0]\n'
PGM = base64.b64encode(b'P2\n2 2\n255\n255 0 128 255\n').decode()


class MapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.manager = MapManager(self.root / 'maps', self.root / 'worker.sh')

    def tearDown(self):
        self.manager.stop()
        self.temp.cleanup()

    def test_import_persists_portable_pair_and_lists(self):
        self.manager.save('casa', YAML, PGM)
        result = self.manager.read('casa')
        self.assertIn('image: map.pgm', result['yaml'])
        self.assertEqual(result['pgm_base64'], PGM)
        reopened = MapManager(self.manager.root, self.manager.worker)
        self.assertEqual(reopened.list(), [{'name': 'casa', 'source': 'imported'}])

    def test_does_not_overwrite(self):
        self.manager.save('casa', YAML, PGM)
        with self.assertRaises(FileExistsError):
            self.manager.save('casa', YAML, PGM)
        self.assertEqual(self.manager.read('casa')['pgm_base64'], PGM)

    def test_invalid_input_never_appears_in_library(self):
        for name, yaml, pgm in [('..', YAML, PGM), ('a;rm', YAML, PGM),
                                ('bad', 'not-yaml', PGM), ('bad', YAML, '???'),
                                ('bad', YAML, base64.b64encode(b'not-pgm').decode())]:
            with self.assertRaises(ValueError):
                self.manager.save(name, yaml, pgm)
        self.assertEqual(self.manager.list(), [])

    def test_disabled_mode_never_launches_ros(self):
        with patch('app.mapping.subprocess.Popen') as popen:
            with self.assertRaises(ValueError):
                self.manager.start()
            with self.assertRaises(ValueError):
                self.manager.save('casa')
            popen.assert_not_called()

    def test_missing_map(self):
        with self.assertRaises(FileNotFoundError):
            self.manager.read('missing')

    def test_ros_requires_validated_params(self):
        self.manager.enabled = True
        with patch.dict(os.environ, {'ONIGIRI_SLAM_PARAMS': ''}):
            with self.assertRaises(ValueError):
                self.manager.start()

    def test_experimental_still_requires_server_enable(self):
        with patch('app.mapping.subprocess.Popen') as popen:
            with self.assertRaises(ValueError):
                self.manager.start(experimental=True)
            popen.assert_not_called()

    @unittest.skipUnless(os.name == 'posix', 'Linux process groups')
    def test_experimental_uses_separate_worker_operation(self):
        self.manager.worker.write_text('test "$1" = start-experimental || exit 7\nexec sleep 60\n')
        self.manager.enabled = True
        with patch.dict(os.environ, {'ONIGIRI_SLAM_PARAMS': ''}):
            status = self.manager.start(experimental=True)
            self.assertTrue(status['running'])
            self.assertEqual(status['profile'], 'experimental-default')
            self.assertEqual(self.manager.process.args[-1], 'start-experimental')
            self.manager.stop()

    @unittest.skipUnless(os.name == 'posix', 'Linux process groups')
    def test_worker_lifecycle_and_save(self):
        self.manager.worker.write_text('''#!/bin/bash
case "$1" in
start) exec sleep 60 ;;
save) printf 'image: map.pgm\\nresolution: 0.05\\norigin: [0, 0, 0]\\n' > "$2.yaml"
printf 'P2\\n1 1\\n255\\n255\\n' > "$2.pgm" ;;
esac
''')
        params = self.root / 'params.yaml'
        params.write_text('placeholder for test worker')
        self.manager.enabled = True
        with patch.dict(os.environ, {'ONIGIRI_SLAM_PARAMS': str(params)}):
            self.assertTrue(self.manager.start()['running'])
            pid = self.manager.process.pid
            self.manager.start()
            self.assertEqual(self.manager.process.pid, pid)
            self.assertEqual(self.manager.save('captura')['source'], 'ros')
            self.assertFalse(self.manager.stop()['running'])
            self.assertFalse(self.manager.stop()['running'])


if __name__ == '__main__':
    unittest.main()
