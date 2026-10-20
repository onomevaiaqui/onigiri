import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from app.mapping import MapManager
from app.stationary_slam import commands


class StationaryTests(unittest.TestCase):
    def test_only_stationary_profile_adds_tf(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            worker=root/'worker.sh'
            worker.write_text('case "$1" in start-stationary) exec sleep 60 ;; esac\n')
            manager=MapManager(root/'maps',worker,enabled=True)
            try:
                with patch.dict(os.environ,{'ONIGIRI_SLAM_PARAMS':''}):
                    result=manager.start(stationary=True)
                    self.assertEqual(result['profile'],'stationary-preview')
                    self.assertEqual(manager.process.args[-1],'start-stationary')
                    self.assertIn('imóvel',result['detail'])
            finally:manager.stop()

    def test_commands_never_drive_robot(self):
        items=commands()
        self.assertEqual(len(items),3)
        self.assertEqual(items[0][-4:],['--frame-id','odom','--child-frame-id','base_footprint'])
        self.assertEqual(items[1][-4:],['--frame-id','base_footprint','--child-frame-id','laser'])
        self.assertIn('use_sim_time:=false',items[2])
        self.assertNotIn('cmd_vel',' '.join(sum(items,[])))

    @unittest.skipUnless(os.name=='posix','Linux supervisor lifecycle')
    def test_supervisor_stops_all_child_groups(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            fake=root/'ros2'
            fake.write_text('#!/bin/sh\necho $$ >> "$TEST_PIDS"\nexec sleep 60\n')
            fake.chmod(0o755)
            env=os.environ.copy();env['PATH']=str(root)+':'+env['PATH'];env['TEST_PIDS']=str(root/'pids')
            script=Path(__file__).parents[1]/'app/stationary_slam.py'
            supervisor=subprocess.Popen([sys.executable,'-c',
                'import sys; sys.path.insert(0,sys.argv[1]); from stationary_slam import run; raise SystemExit(run())',
                str(script.parent)],env=env,start_new_session=True)
            try:
                for _ in range(100):
                    if (root/'pids').exists() and len((root/'pids').read_text().splitlines())==3:break
                    time.sleep(.02)
                else:self.fail('Os três processos não iniciaram')
                pids=[int(p) for p in (root/'pids').read_text().splitlines()]
                supervisor.terminate();supervisor.wait(timeout=5)
                for pid in pids:
                    with self.assertRaises(ProcessLookupError):os.kill(pid,0)
            finally:
                if supervisor.poll() is None:os.killpg(supervisor.pid,signal.SIGKILL);supervisor.wait()
