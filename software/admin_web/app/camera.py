"""Owns only a read-only camera subscriber; never starts a motor or camera driver."""
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import threading
import time

class CameraPreview:
    def __init__(self, worker, enabled=False):
        self.worker=Path(worker);self.enabled=enabled
        self.process=None;self.directory=None;self.lock=threading.RLock()
    def start(self):
        with self.lock:
            if not self.enabled:raise ValueError("Active ONIGIRI_CAMERA_PREVIEW_ENABLED=1 no servidor ROS")
            if self.process and self.process.poll() is None:return self.status()
            self.stop();self.directory=tempfile.TemporaryDirectory(prefix="onigiri-camera-")
            try:
                self.process=subprocess.Popen(["bash",str(self.worker),str(Path(self.directory.name)/"snapshot.json")],start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            except Exception:
                self.stop();raise
            return self.status()
    def stop(self):
        with self.lock:
            if self.process and self.process.poll() is None:
                os.killpg(self.process.pid,signal.SIGTERM)
                try:self.process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(self.process.pid,signal.SIGKILL);self.process.wait(timeout=3)
            self.process=None
            if self.directory:self.directory.cleanup();self.directory=None
            return {"enabled":self.enabled,"running":False,"state":"idle"}
    def status(self):
        with self.lock:
            running=self.process is not None and self.process.poll() is None
            result={"enabled":self.enabled,"running":running,"state":"waiting" if running else "failed" if self.process else "idle"}
            if running and self.directory:
                path=Path(self.directory.name)/"snapshot.json"
                if path.exists():
                    try:
                        data=json.loads(path.read_text());age=max(0,time.time()-data['received_at'])
                        result.update(data);result['age_seconds']=round(age,1)
                        result['state']='error' if 'error' in data else 'live' if age<3 else 'stale'
                    except (ValueError,KeyError,OSError):pass
            return result
