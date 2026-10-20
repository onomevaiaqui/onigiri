import json
import struct
import tempfile
import time
import unittest
import zlib
from pathlib import Path
from unittest.mock import Mock

from app.mapping import MapManager
from app.map_preview_ros import map_png, MapRevision


class PreviewTests(unittest.TestCase):
    def test_repeated_messages_are_not_map_changes(self):
        revision=MapRevision()
        self.assertEqual(revision.update(b'image',[.05,0,0],100),{'revision':1,'changed_at':100})
        self.assertEqual(revision.update(b'image',[.05,0,0],110),{'revision':1,'changed_at':100})
        self.assertEqual(revision.update(b'new image',[.05,0,0],120),{'revision':2,'changed_at':120})
        self.assertEqual(revision.update(b'new image',[.05,1,0],130),{'revision':3,'changed_at':130})

    def test_png_orientation_and_occupancy(self):
        png=map_png(2,2,bytes([0,100,255,50]))
        self.assertEqual(png[:8],b'\x89PNG\r\n\x1a\n')
        length=struct.unpack('!I',png[33:37])[0]
        rows=zlib.decompress(png[41:41+length])
        self.assertEqual(rows,bytes([0,205,128,0,255,0]))

    def test_rejects_invalid_or_oversized_grid(self):
        for width,height,cells in [(0,1,b''),(5000,1,b''),(2,2,b'\x00')]:
            with self.assertRaises(ValueError):map_png(width,height,cells)

    def test_states_snapshot_staleness_and_stop_cleanup(self):
        with tempfile.TemporaryDirectory() as root:
            manager=MapManager(Path(root),Path(root)/'worker')
            self.assertEqual(manager.preview()['state'],'disabled')
            manager.enabled=True
            self.assertEqual(manager.preview()['state'],'idle')
            manager.process=Mock();manager.process.poll.return_value=None
            self.assertEqual(manager.preview()['state'],'waiting')
            manager.preview_directory=tempfile.TemporaryDirectory(dir=root)
            manager.preview_process=Mock();manager.preview_process.poll.return_value=None
            snapshot=Path(manager.preview_directory.name)/'snapshot.json'
            snapshot.write_text(json.dumps({'received_at':time.time(),'png_base64':'sample'}))
            self.assertEqual(manager.preview()['state'],'live')
            self.assertNotIn('png_base64',manager.preview(after=json.loads(snapshot.read_text())['received_at']))
            self.assertIn('png_base64',manager.preview(after=0))
            snapshot.write_text(json.dumps({'received_at':time.time()-30,'png_base64':'sample'}))
            self.assertEqual(manager.preview()['state'],'stale')
            snapshot.write_text('{bad json')
            self.assertEqual(manager.preview()['state'],'waiting')
            manager.preview_process.poll.return_value=1
            self.assertEqual(manager.preview()['state'],'error')
            manager.process.poll.return_value=0
            directory=snapshot.parent
            manager.stop()
            self.assertFalse(directory.exists())
            self.assertEqual(manager.preview()['state'],'idle')
