"""Persistent hardware declarations; never opens a motor interface."""
import json
import os
import tempfile
from pathlib import Path
from threading import RLock

CATALOG = [
    {"id": "onigiri", "name": "3 motores com omniball · Onigiri", "description": "Plataforma original Onigiri: dois motores de tração e um motor lateral com omniball", "available": True},
    {"id": "tank", "name": "2 motores com esteiras · Tank", "description": "Tração diferencial: esteira esquerda e direita; sem deslocamento lateral", "available": True},
    {"id": "mecanum", "name": "4 motores com rodas mecanum", "description": "Quatro rodas mecanum; dois controladores Sabertooth, com USB separado ou serial TTL compartilhada", "available": True},
]

def tank_tracks(linear, angular, track_separation):
    """Track speeds in m/s from body linear m/s and angular rad/s (ROS CCW)."""
    if track_separation <= 0:
        raise ValueError("A distância entre esteiras deve ser positiva")
    return {"left": linear-angular*track_separation/2,
            "right": linear+angular*track_separation/2}

class PlatformStore:
    def __init__(self, path):
        self.path = Path(path)
        self.lock = RLock()

    def get(self):
        with self.lock:
            if self.path.exists():
                return json.loads(self.path.read_text(encoding="utf-8"))
            return {"computer": "raspberry4", "motor_driver": "onigiri_hat", "chassis": "onigiri", "track_separation_m": 0.3,
                    "camera": "none", "lidar": True}

    def save(self, config):
        if config["chassis"] not in ("onigiri", "tank", "mecanum"):
            raise ValueError("Plataforma ainda não disponível")
        with self.lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, name = tempfile.mkstemp(dir=self.path.parent, prefix=".platform-")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as stream:
                    json.dump(config, stream, ensure_ascii=False, indent=2)
                os.replace(name, self.path)
            finally:
                Path(name).unlink(missing_ok=True)
        return config
