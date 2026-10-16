"""FastAPI application for the local Onigiri destination panel."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .services import DestinationStore


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATABASE = PROJECT_ROOT / "data" / "onigiri_admin.db"
DEFAULT_EXPORT = PROJECT_ROOT / "config" / "destinations.runtime.json"
SEED_FILE = PROJECT_ROOT / "config" / "destinations.example.json"


class DestinationInput(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    aliases: list[str] = Field(default_factory=list)
    phrases: list[str] = Field(default_factory=list)
    x: float = 0.0
    y: float = 0.0
    yaw: float = 0.0
    arrival_message: str = ""
    wait_seconds: float = Field(default=15.0, ge=0, le=600)
    return_to_base: bool = True


class TextRequest(BaseModel):
    text: Annotated[str, Field(min_length=1, max_length=300)]


def build_store() -> DestinationStore:
    database_path = Path(os.environ.get("ONIGIRI_ADMIN_DATABASE", DEFAULT_DATABASE))
    export_path = Path(os.environ.get("ONIGIRI_DESTINATIONS_FILE", DEFAULT_EXPORT))
    return DestinationStore(database_path, export_path, SEED_FILE)


store = build_store()
app = FastAPI(title="Painel Onigiri", version="0.1.0")
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": "simulation"}


@app.get("/api/destinations")
def list_destinations() -> list[dict]:
    return store.list()


@app.post("/api/destinations", status_code=201)
def create_destination(payload: DestinationInput) -> dict:
    try:
        return store.save(payload.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.put("/api/destinations/{destination_id}")
def update_destination(destination_id: int, payload: DestinationInput) -> dict:
    try:
        return store.save(payload.model_dump(), destination_id)
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
def delete_destination(destination_id: int) -> None:
    try:
        store.delete(destination_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/api/interpret")
def interpret_command(payload: TextRequest) -> dict:
    return store.interpret(payload.text)


@app.post("/api/simulate")
def simulate_command(payload: TextRequest) -> dict:
    return store.simulate(payload.text)


@app.post("/api/export")
def export_destinations() -> dict[str, str]:
    return {"path": str(store.export_ros_config())}
