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
    yield
    maps.stop()


app = FastAPI(title="Painel Onigiri", version="0.1.0", lifespan=lifespan)
from .access import PanelAccess
app.add_middleware(PanelAccess)
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": "configuration-only"}


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
    return {**maps.status(),'perception_source':'lidar'}


@app.get('/api/mapping/preview')
def mapping_preview(after: float | None = None):
    return maps.preview(after)


@app.post('/api/mapping/start')
def mapping_start(payload: MappingStartInput | None = None):
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


# Fixed Onigiri hardware; this panel does not expose actuator commands.
from typing import Literal
from pydantic import ConfigDict
from .platforms import PlatformStore
platforms=PlatformStore(os.environ.get('ONIGIRI_PLATFORM_FILE',PROJECT_ROOT/'data/platform.json'))

class PlatformInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    robot_name: str = Field(default='',max_length=80)
    computer: Literal['raspberry4']='raspberry4'
    chassis: Literal['onigiri']='onigiri'
    motor_driver: Literal['onigiri_hat']='onigiri_hat'
    camera: Literal['none']='none'
    lidar: Literal[True]=True

@app.get('/api/platform')
def get_platform():
    return {'config':platforms.get(),'motor_status':'HAT original; o painel não aciona motores'}

@app.put('/api/platform')
def set_platform(payload:PlatformInput):
    try:return platforms.save(payload.model_dump())
    except OSError:raise HTTPException(500,'Não foi possível salvar a configuração')


class WifiInput(BaseModel):
    ssid: str = Field(min_length=1,max_length=32)
    password: str = Field(min_length=8,max_length=63)

@app.get('/api/setup/network')
def setup_network():
    from .network import request
    try:return request('/api/setup/network')
    except (OSError,ValueError):return {'enabled':False,'mode':'unavailable','message':'Configuração de Wi-Fi não instalada neste dispositivo.','addresses':[]}

@app.post('/api/setup/network/connect',status_code=202)
def setup_wifi(payload: WifiInput):
    if maps.status()['running']:
        raise HTTPException(409,'Encerre o mapeamento antes de trocar a rede')
    from .network import request
    try:return request('/api/setup/network/connect',payload.model_dump())
    except OSError:raise HTTPException(503,'Serviço de rede indisponível')
    except ValueError as error:raise HTTPException(400,str(error))
