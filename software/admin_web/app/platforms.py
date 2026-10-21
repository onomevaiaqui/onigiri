"""Persist the supported Onigiri hardware profile without opening devices."""
import json
import os
import tempfile
from pathlib import Path
from threading import RLock

CHASSIS_CATALOG = [
    {"id": "omniball", "name": "3 rodas omniball", "description": "Base holonômica com três motores; permite deslocamento lateral."},
    {"id": "mecanum", "name": "4 rodas mecanum", "description": "Base holonômica com quatro motores e rodas mecanum."},
]

# A driver can be selected and saved for commissioning. Only the original HAT
# has a reviewed runtime adapter in this repository.
DRIVER_CATALOG = [
    {"id":"onigiri_hat","name":"HAT original do Onigiri","channels":3,"connection":"i2c","operational":True},
    {"id":"sabertooth2x32","name":"Dimension Engineering Sabertooth 2x32","channels":2,"connection":"usb","operational":False},
    {"id":"sabertooth2x60","name":"Dimension Engineering Sabertooth 2x60","channels":2,"connection":"usb_ttl","operational":False},
    {"id":"sabertooth2x12","name":"Dimension Engineering Sabertooth 2x12","channels":2,"connection":"usb_ttl","operational":False},
    {"id":"sabertooth2x25","name":"Dimension Engineering Sabertooth 2x25","channels":2,"connection":"usb_ttl","operational":False},
    {"id":"roboclaw","name":"Ion Motion Control RoboClaw (dual)","channels":2,"connection":"usb","operational":False},
    {"id":"cytron_mdds","name":"Cytron SmartDriveDuo MDDS","channels":2,"connection":"usb_ttl","operational":False},
    {"id":"cytron_mdd10a","name":"Cytron MDD10A · ponte H dupla 10 A","channels":2,"connection":"gpio_pwm_dir","operational":False},
    {"id":"cytron_mdd20a","name":"Cytron MDD20A · ponte H dupla 20 A","channels":2,"connection":"gpio_pwm_dir","operational":False},
    {"id":"robocore_2x40a","name":"RoboCore 2x40A · ponte H dupla","channels":2,"connection":"gpio_pwm_dir","operational":False},
    {"id":"l298n","name":"L298N · ponte H dupla educacional","channels":2,"connection":"gpio_pwm_dir","operational":False},
    {"id":"tb6612fng","name":"TB6612FNG · ponte H dupla baixa tensão","channels":2,"connection":"gpio_pwm_dir","operational":False},
    {"id":"drv8833","name":"DRV8833 · ponte H dupla baixa tensão","channels":2,"connection":"gpio_pwm_dir","operational":False},
    {"id":"bts7960","name":"BTS7960 / IBT-2 · ponte H de alta corrente","channels":1,"connection":"gpio_pwm_dir","operational":False},
    {"id":"generic_pwm_dir_dual","name":"Ponte H dupla genérica PWM/DIR","channels":2,"connection":"gpio_pwm_dir","operational":False},
]

LIDAR_CATALOG = [
    {"id":"rplidar","name":"Slamtec RPLIDAR A1/A2/A3/S1","driver":"rplidar_ros","operational":True},
    {"id":"ldlidar","name":"LDROBOT LD06/LD19","driver":"ldlidar_stl_ros2","operational":False},
    {"id":"ydlidar","name":"YDLIDAR X2/X4/G2/G4","driver":"ydlidar_ros2_driver","operational":False},
    {"id":"generic_scan","name":"LiDAR 2D com tópico ROS 2 /scan","driver":"externo","operational":True},
]

CAMERA_CATALOG = [
    {"id":"none","name":"Sem webcam"},
    {"id":"uvc","name":"Webcam UVC com microfone"},
]

DRIVER_BY_ID = {item["id"]: item for item in DRIVER_CATALOG}
LIDAR_BY_ID = {item["id"]: item for item in LIDAR_CATALOG}

DEFAULT = {
    "robot_name":"", "computer":"raspberry4", "chassis":"omniball",
    "motor_driver":"onigiri_hat", "motor_connection":"i2c", "serial_port":"",
    "lidar_model":"rplidar", "lidar_port":"", "camera":"uvc",
    "camera_device":"/dev/video0", "microphone_device":"default", "speaker_device":"default",
}

class PlatformStore:
    def __init__(self, path):
        self.path = Path(path)
        self.lock = RLock()

    def get(self):
        with self.lock:
            try:
                saved = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
            except (OSError, json.JSONDecodeError):
                saved = {}
            if saved.get("chassis") == "onigiri":
                saved["chassis"] = "omniball"
            return {**DEFAULT, **{key: value for key, value in saved.items() if key in DEFAULT}}

    def save(self, config):
        if config["motor_driver"] not in DRIVER_BY_ID:
            raise ValueError("Controlador de motores fora do catálogo")
        if config["lidar_model"] not in LIDAR_BY_ID:
            raise ValueError("LiDAR fora do catálogo")
        if config["motor_connection"] != DRIVER_BY_ID[config["motor_driver"]]["connection"]:
            raise ValueError("Conexão incompatível com o controlador selecionado")
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
