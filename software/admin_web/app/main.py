"""FastAPI application for the local Onigiri destination panel."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .services import DestinationStore
from .mapping import MapManager


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATABASE = PROJECT_ROOT / "data" / "onigiri_admin.db"
DEFAULT_EXPORT = PROJECT_ROOT / "config" / "destinations.runtime.json"
SEED_FILE = PROJECT_ROOT / "config" / "destinations.example.json"


class DestinationInput(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    map_name: str | None = Field(default=None, max_length=60, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")
    aliases: list[str] = Field(default_factory=list)
    phrases: list[str] = Field(default_factory=list)
    x: float = Field(default=0, allow_inf_nan=False, ge=-10000, le=10000)
    y: float = Field(default=0, allow_inf_nan=False, ge=-10000, le=10000)
    yaw: float = Field(default=0, allow_inf_nan=False, ge=-7, le=7)
    arrival_message: str = ""
    wait_seconds: float = Field(default=15.0, ge=0, le=600)
    return_to_base: bool = True
    is_home: bool | None = None


class TextRequest(BaseModel):
    text: Annotated[str, Field(min_length=1, max_length=300)]


class TextBatchRequest(BaseModel):
    texts: list[Annotated[str, Field(min_length=1, max_length=300)]] = Field(
        min_length=1, max_length=50
    )


class BackupInput(BaseModel):
    format: str
    version: int
    destinations: list[dict]


def build_store() -> DestinationStore:
    database_path = Path(os.environ.get("ONIGIRI_ADMIN_DATABASE", DEFAULT_DATABASE))
    export_path = Path(os.environ.get("ONIGIRI_DESTINATIONS_FILE", DEFAULT_EXPORT))
    return DestinationStore(database_path, export_path, SEED_FILE)


store = build_store()
maps = MapManager(Path(os.environ.get('ONIGIRI_MAPS_DIR', PROJECT_ROOT / 'data' / 'maps')),
                  PROJECT_ROOT / 'deploy' / 'scripts' / 'mapping_worker.sh',
                  os.environ.get('ONIGIRI_MAPPING_ENABLED') == '1')


@asynccontextmanager
async def lifespan(app):
    if os.environ.get('ONIGIRI_CAMERA_AUTOSTART')=='1' and platforms.get().get('camera')=='gemini2' and camera_driver.enabled:
        camera_driver.start()
        if camera_preview.enabled:camera_preview.start()
    yield
    maps.stop()
    camera_preview.stop()
    navigation_stack.stop()
    robot_bridge.stop()
    camera_driver.stop()


app = FastAPI(title="Painel Onigiri", version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": "robotics-enabled" if os.environ.get("ONIGIRI_MOTION_ENABLED")=="1" else "simulation"}


@app.get("/api/destinations")
def list_destinations() -> list[dict]:
    return store.list()


@app.post("/api/destinations", status_code=201)
def create_destination(payload: DestinationInput) -> dict:
    try:
        return store.save(payload.model_dump(exclude_unset=True))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.put("/api/destinations/{destination_id}")
def update_destination(destination_id: int, payload: DestinationInput) -> dict:
    try:
        return store.save(payload.model_dump(exclude_unset=True), destination_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/api/destinations/{destination_id}/home")
def set_home(destination_id: int) -> dict:
    try:
        return store.set_home(destination_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.delete("/api/destinations/{destination_id}", status_code=204)
def delete_destination(destination_id: int, replacement_id: int | None = None) -> None:
    try:
        store.delete(destination_id, replacement_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/api/interpret")
def interpret_command(payload: TextRequest) -> dict:
    return store.interpret(payload.text)


@app.post("/api/interpret/batch")
def interpret_batch(payload: TextBatchRequest) -> dict[str, list[dict]]:
    return {"results": [store.interpret(text) for text in payload.texts]}


@app.post("/api/simulate")
def simulate_command(payload: TextRequest) -> dict:
    return store.simulate(payload.text)


@app.post("/api/export")
def export_destinations() -> dict[str, str]:
    return {"path": str(store.export_ros_config())}


@app.get("/api/readiness")
def readiness() -> dict:
    return store.readiness()


@app.get("/api/backup")
def backup() -> dict:
    return store.backup()


@app.post("/api/backup/restore")
def restore_backup(payload: BackupInput) -> list[dict]:
    try:
        return store.restore(payload.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


class MapInput(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    yaml: str | None = Field(default=None, max_length=100_000)
    pgm_base64: str | None = Field(default=None, max_length=16_000_000)


class MappingStartInput(BaseModel):
    experimental: bool = False
    stationary: bool = False
    lidar_odometry: bool = False


def map_action(action, *args):
    try:
        return action(*args)
    except FileExistsError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except OSError as error:
        raise HTTPException(status_code=503, detail='Falha ao acessar o serviço ou os arquivos de mapas.') from error


@app.get('/api/mapping')
def mapping_status():
    return maps.status()


@app.get('/api/mapping/preview')
def mapping_preview(after: float | None = None):
    return maps.preview(after)


@app.post('/api/mapping/start')
def mapping_start(payload: MappingStartInput | None = None):
    if navigation_stack.status()["running"]:
        raise HTTPException(409,"Encerre a navegação antes de iniciar SLAM")
    return map_action(maps.start, payload.experimental if payload else False, payload.stationary if payload else False,
                      payload.lidar_odometry if payload else False)


@app.post('/api/mapping/stop')
def mapping_stop():
    return map_action(maps.stop)


@app.get('/api/maps')
def map_list():
    return map_action(maps.list)


@app.get('/api/maps/{name}')
def map_read(name: str):
    return map_action(maps.read, name)


@app.post('/api/maps', status_code=201)
def map_save(payload: MapInput):
    if (payload.yaml is None) != (payload.pgm_base64 is None):
        raise HTTPException(status_code=400, detail='Envie YAML e PGM juntos para guardar um mapa local.')
    return map_action(maps.save, payload.name, payload.yaml, payload.pgm_base64)


# Hardware declarations do not change running ROS or motor services.
from typing import Literal
from .platforms import PlatformStore, CATALOG
platforms = PlatformStore(os.environ.get("ONIGIRI_PLATFORM_FILE", PROJECT_ROOT / "data" / "platform.json"))

class PlatformInput(BaseModel):
    computer: Literal["raspberry4", "raspberry5"] = "raspberry4"
    motor_driver: Literal["onigiri_hat", "sabertooth2x32", "sabertooth2x60"] = "onigiri_hat"
    motor_connection: Literal["i2c", "usb", "usb_ttl"] = "i2c"
    serial_port: str = Field(default="", max_length=240, pattern=r"^(/dev/[A-Za-z0-9_./:-]+)?$")
    serial_address: int = Field(default=128, ge=128, le=135)
    serial_baud: Literal[9600, 19200, 38400] = 9600
    chassis: Literal["onigiri", "tank", "mecanum"] = "onigiri"
    wheelbase_m: float = Field(default=0.3, ge=0.05, le=3, allow_inf_nan=False)
    max_track_speed_mps: float = Field(default=0.3, ge=0.01, le=2, allow_inf_nan=False)
    power_limit: float = Field(default=0.2, ge=0.01, le=1, allow_inf_nan=False)
    motor_inversions: list[bool] = Field(default_factory=lambda: [False,False], min_length=2, max_length=4)
    serial_port_2: str = Field(default="", max_length=240, pattern=r"^(/dev/[A-Za-z0-9_./:-]+)?$")
    body_width_m: float = Field(default=0.5, ge=0.1, le=3, allow_inf_nan=False)
    body_length_m: float = Field(default=0.5, ge=0.1, le=3, allow_inf_nan=False)
    serial_address_2: int = Field(default=129, ge=128, le=135)
    extrinsics_measured: bool = False
    lidar_xyz_rpy: list[float] = Field(default_factory=lambda: [0.0]*6, min_length=6, max_length=6)
    camera_xyz_rpy: list[float] = Field(default_factory=lambda: [0.0]*6, min_length=6, max_length=6)
    track_separation_m: float = Field(default=0.3, ge=0.05, le=3, allow_inf_nan=False)
    camera: Literal["none", "gemini2"] = "none"
    lidar: bool = True

@app.get("/api/platform")
def get_platform():
    return {"config": platforms.get(), "catalog": CATALOG,
            "motor_status": "Configuração declarada; controlador não conectado pelo painel",
            "camera_status": "Configuração declarada; captura não iniciada pelo painel"}

@app.put("/api/platform")
def set_platform(payload: PlatformInput):
    if navigation_stack.status()["running"]:
        raise HTTPException(409,"Encerre a navegação antes de alterar o chassi")
    if payload.chassis != "onigiri" and payload.motor_driver == "onigiri_hat":
        raise HTTPException(422, "Selecione um Sabertooth para o tank")
    if payload.chassis == "onigiri" and payload.motor_driver != "onigiri_hat":
        raise HTTPException(422, "O perfil original usa o HAT do Onigiri")
    import math
    if not all(math.isfinite(v) and abs(v)<=20 for v in payload.lidar_xyz_rpy+payload.camera_xyz_rpy):
        raise HTTPException(422, "Extrínsecas inválidas")
    channels = 4 if payload.chassis == "mecanum" else 3 if payload.chassis == "onigiri" else 2
    if "motor_inversions" not in payload.model_fields_set:payload.motor_inversions=[False]*channels
    if len(payload.motor_inversions) != channels:
        raise HTTPException(422, "Confira o número de motores")
    if channels == 4 and payload.serial_address == payload.serial_address_2:
        raise HTTPException(422, "Os dois controladores precisam de endereços diferentes")
    expected_connection = {"onigiri_hat": "i2c", "sabertooth2x32": "usb", "sabertooth2x60": "usb_ttl"}[payload.motor_driver]
    if payload.motor_connection != expected_connection:
        raise HTTPException(422, "Conexão incompatível com o controlador selecionado")
    try:
        return platforms.save(payload.model_dump())
    except OSError as error:
        raise HTTPException(500, "Não foi possível salvar a configuração") from error


class TankPreviewInput(BaseModel):
    forward: float = Field(default=0, ge=-1, le=1, allow_inf_nan=False)
    turn: float = Field(default=0, ge=-1, le=1, allow_inf_nan=False)
    address: int = Field(default=128, ge=128, le=135)
    invert_left: bool = False
    invert_right: bool = False

@app.post("/api/platform/tank/preview")
def preview_tank(payload: TankPreviewInput):
    from .sabertooth import tank_preview
    return tank_preview(**payload.model_dump())


from .camera import CameraPreview
camera_preview = CameraPreview(PROJECT_ROOT / "deploy/scripts/camera_preview_worker.sh",
    os.environ.get("ONIGIRI_CAMERA_PREVIEW_ENABLED") == "1")

@app.get("/api/sensors/camera/preview")
def get_camera_preview():
    return camera_preview.status()

@app.post("/api/sensors/camera/preview/start")
def start_camera_preview():
    if platforms.get().get("camera") != "gemini2":
        raise HTTPException(409, "Selecione a Gemini 2 nas configurações")
    try:
        return camera_preview.start()
    except ValueError as error:
        raise HTTPException(409, str(error)) from error

@app.post("/api/sensors/camera/preview/stop")
def stop_camera_preview():
    return camera_preview.stop()


from .runtime import Process
robot_bridge = Process(PROJECT_ROOT / "deploy/scripts/robot_bridge_worker.sh", os.environ.get("ONIGIRI_RUNTIME_ENABLED") == "1")
navigation_stack = Process(PROJECT_ROOT / "deploy/scripts/navigation_worker.sh", os.environ.get("ONIGIRI_RUNTIME_ENABLED") == "1")
camera_driver = Process(PROJECT_ROOT / "deploy/scripts/camera_driver_worker.sh", os.environ.get("ONIGIRI_CAMERA_DRIVER_ENABLED") == "1")

class NavigationMapInput(BaseModel):
    name: str = Field(min_length=1, max_length=60)

class InitialPoseInput(BaseModel):
    x: float = Field(allow_inf_nan=False, ge=-10000, le=10000)
    y: float = Field(allow_inf_nan=False, ge=-10000, le=10000)
    yaw: float = Field(default=0, allow_inf_nan=False, ge=-7, le=7)

@app.get("/api/runtime")
def runtime_status():
    return {"bridge":robot_bridge.status(), "navigation":navigation_stack.status(),
            "camera_driver":camera_driver.status(), "map_name":getattr(navigation_stack,"map_name",None) if navigation_stack.status()["running"] else None, "motion_enabled":os.environ.get("ONIGIRI_MOTION_ENABLED")=="1"}

@app.post("/api/runtime/connect")
def runtime_connect():
    return map_action(robot_bridge.start)

@app.post("/api/runtime/disconnect")
def runtime_disconnect():
    navigation_stack.stop()
    return robot_bridge.stop()

@app.post("/api/runtime/navigation/start")
def runtime_navigation_start(payload:NavigationMapInput):
    if maps.status()['running']:
        raise HTTPException(409,"Encerre o SLAM antes de iniciar localização Nav2")
    config=platforms.get()
    if not config.get('extrinsics_measured'):
        raise HTTPException(409,"Meça e confirme as posições dos sensores primeiro")
    name=map_action(maps.valid_name,payload.name)
    if navigation_stack.status()["running"]:
        if getattr(navigation_stack,"map_name",None)!=name:
            raise HTTPException(409,"Encerre a navegação para trocar de mapa")
        return navigation_stack.status()
    metadata=maps.metadata(maps.root/name)
    if metadata.get('profile')=='stationary-preview':
        raise HTTPException(409,"Captura com TF fixas não pode ser usada para navegação")
    path=maps.root/name/'map.yaml'
    if not path.is_file():raise HTTPException(404,"Mapa não encontrado")
    result=map_action(navigation_stack.start,path)
    navigation_stack.map_name=name
    return result

@app.post("/api/runtime/navigation/stop")
def runtime_navigation_stop():
    if robot_bridge.status()['running']:robot_bridge.send('cancel')
    return navigation_stack.stop()

@app.post("/api/runtime/initial-pose")
def runtime_initial_pose(payload:InitialPoseInput):
    return runtime_send('initial_pose',**payload.model_dump())

@app.post("/api/runtime/destinations/{destination_id}/go")
def runtime_go(destination_id:int):
    if os.environ.get('ONIGIRI_MOTION_ENABLED')!='1':raise HTTPException(409,'Movimento não habilitado no servidor')
    destination=next((d for d in store.list() if d['id']==destination_id),None)
    if not destination:raise HTTPException(404,'Destino não encontrado')
    import math
    if not all(math.isfinite(destination[key]) for key in ('x','y','yaw')):raise HTTPException(409,'Coordenadas inválidas')
    current_map=getattr(navigation_stack,'map_name',None)
    if not navigation_stack.status()['running'] or not current_map or destination.get('map_name')!=current_map:
        raise HTTPException(409,'Associe o destino ao mesmo mapa salvo usado na navegação')
    return runtime_send('navigate',x=destination['x'],y=destination['y'],yaw=destination['yaw'])

@app.post("/api/runtime/base/{operation}")
def runtime_base(operation:str):
    if operation not in ('arm','cancel','emergency_stop','release'):raise HTTPException(404,'Operação inválida')
    if operation in ('arm','release') and os.environ.get('ONIGIRI_MOTION_ENABLED')!='1':raise HTTPException(409,'Movimento não habilitado no servidor')
    return map_action(robot_bridge.send,operation)

@app.post("/api/sensors/camera/driver/{operation}")
def runtime_camera_driver(operation:str):
    if operation=='stop':
        camera_preview.stop();return camera_driver.stop()
    if operation!='start':raise HTTPException(404,'Operação inválida')
    if platforms.get().get('camera')!='gemini2':raise HTTPException(409,'Selecione a Gemini 2')
    return map_action(camera_driver.start)


def runtime_send(operation,**kwargs):
    try:return robot_bridge.send(operation,**kwargs)
    except ValueError as error:raise HTTPException(409,str(error)) from error
