"""Persistence and command interpretation for the Onigiri admin panel.

The panel keeps its editable records in SQLite and exports a ROS-compatible
destinations JSON file after every change. The future ROS 2 mission node can
read that exported file without depending on the web application at runtime.
"""

from __future__ import annotations

import json
import sqlite3
import unicodedata
from contextlib import contextmanager
from pathlib import Path
from typing import Any


def normalize(text: str) -> str:
    """Normalize Portuguese text for accent-insensitive matching."""
    decomposed = unicodedata.normalize("NFD", text.casefold().strip())
    return "".join(character for character in decomposed if not unicodedata.combining(character))


def split_lines(value: str | list[str]) -> list[str]:
    """Clean user supplied aliases or phrases while preserving order."""
    items = value.splitlines() if isinstance(value, str) else value
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in items:
        item = item.strip()
        key = normalize(item)
        if item and key not in seen:
            cleaned.append(item)
            seen.add(key)
    return cleaned


class DestinationStore:
    """SQLite store with a JSON export compatible with the ROS mission node."""

    def __init__(self, database_path: Path, export_path: Path, seed_path: Path) -> None:
        self.database_path = database_path
        self.export_path = export_path
        self.seed_path = seed_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connection(self):
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS destinations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                    aliases TEXT NOT NULL DEFAULT '[]',
                    phrases TEXT NOT NULL DEFAULT '[]',
                    x REAL NOT NULL DEFAULT 0,
                    y REAL NOT NULL DEFAULT 0,
                    yaw REAL NOT NULL DEFAULT 0,
                    arrival_message TEXT NOT NULL,
                    wait_seconds REAL NOT NULL DEFAULT 15,
                    return_to_base INTEGER NOT NULL DEFAULT 1,
                    is_home INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            count = connection.execute("SELECT COUNT(*) FROM destinations").fetchone()[0]
            if count == 0:
                self._seed(connection)
        self.export_ros_config()

    def _seed(self, connection: sqlite3.Connection) -> None:
        """Populate the first local database from the versioned example file."""
        seed = json.loads(self.seed_path.read_text(encoding="utf-8"))
        home_name = seed.get("home")
        for item in seed.get("destinations", []):
            name = item["name"].strip()
            connection.execute(
                """
                INSERT INTO destinations
                (name, aliases, phrases, x, y, yaw, arrival_message, wait_seconds, return_to_base, is_home)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    json.dumps(split_lines(item.get("aliases", [])), ensure_ascii=False),
                    json.dumps(split_lines(item.get("phrases", [])), ensure_ascii=False),
                    float(item.get("x", 0.0)),
                    float(item.get("y", 0.0)),
                    float(item.get("yaw", 0.0)),
                    item.get("arrival_message", f"Chegamos a {name}."),
                    float(item.get("wait_seconds", 15.0)),
                    1 if item.get("return_to_base", True) else 0,
                    1 if item.get("name") == home_name else 0,
                ),
            )

    @staticmethod
    def _record(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "name": row["name"],
            "aliases": json.loads(row["aliases"]),
            "phrases": json.loads(row["phrases"]),
            "x": row["x"],
            "y": row["y"],
            "yaw": row["yaw"],
            "arrival_message": row["arrival_message"],
            "wait_seconds": row["wait_seconds"],
            "return_to_base": bool(row["return_to_base"]),
            "is_home": bool(row["is_home"]),
        }

    def list(self) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM destinations ORDER BY is_home DESC, name COLLATE NOCASE"
            ).fetchall()
        return [self._record(row) for row in rows]

    def get(self, destination_id: int) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute("SELECT * FROM destinations WHERE id = ?", (destination_id,)).fetchone()
        return self._record(row) if row else None

    def save(self, values: dict[str, Any], destination_id: int | None = None) -> dict[str, Any]:
        name = values["name"].strip()
        if not name:
            raise ValueError("Informe o nome do destino.")
        aliases = split_lines(values.get("aliases", []))
        phrases = split_lines(values.get("phrases", []))
        arrival_message = values.get("arrival_message", "").strip() or f"Chegamos a {name}."
        payload = (
            name,
            json.dumps(aliases, ensure_ascii=False),
            json.dumps(phrases, ensure_ascii=False),
            float(values.get("x", 0.0)),
            float(values.get("y", 0.0)),
            float(values.get("yaw", 0.0)),
            arrival_message,
            max(0.0, float(values.get("wait_seconds", 15.0))),
            1 if values.get("return_to_base", True) else 0,
        )
        try:
            with self._connection() as connection:
                if destination_id is None:
                    cursor = connection.execute(
                        """
                        INSERT INTO destinations
                        (name, aliases, phrases, x, y, yaw, arrival_message, wait_seconds, return_to_base)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        payload,
                    )
                    destination_id = int(cursor.lastrowid)
                else:
                    result = connection.execute(
                        """
                        UPDATE destinations SET
                        name = ?, aliases = ?, phrases = ?, x = ?, y = ?, yaw = ?,
                        arrival_message = ?, wait_seconds = ?, return_to_base = ?
                        WHERE id = ?
                        """,
                        (*payload, destination_id),
                    )
                    if result.rowcount == 0:
                        raise KeyError("Destino não encontrado.")
        except sqlite3.IntegrityError as error:
            raise ValueError("Já existe um destino com esse nome.") from error
        self.export_ros_config()
        saved = self.get(destination_id)
        assert saved is not None
        return saved

    def set_home(self, destination_id: int) -> dict[str, Any]:
        with self._connection() as connection:
            if connection.execute("SELECT 1 FROM destinations WHERE id = ?", (destination_id,)).fetchone() is None:
                raise KeyError("Destino não encontrado.")
            connection.execute("UPDATE destinations SET is_home = 0")
            connection.execute("UPDATE destinations SET is_home = 1 WHERE id = ?", (destination_id,))
        self.export_ros_config()
        result = self.get(destination_id)
        assert result is not None
        return result

    def delete(self, destination_id: int) -> None:
        destination = self.get(destination_id)
        if destination is None:
            raise KeyError("Destino não encontrado.")
        if destination["is_home"]:
            raise ValueError("Defina outro destino como base antes de excluir este.")
        with self._connection() as connection:
            connection.execute("DELETE FROM destinations WHERE id = ?", (destination_id,))
        self.export_ros_config()

    def export_ros_config(self) -> Path:
        records = self.list()
        home = next((record["name"] for record in records if record["is_home"]), None)
        if home is None and records:
            home = records[0]["name"]
        payload = {
            "home": home,
            "destinations": [
                {
                    "name": record["name"],
                    "aliases": split_lines([*record["aliases"], *record["phrases"]]),
                    "x": record["x"],
                    "y": record["y"],
                    "yaw": record["yaw"],
                    "arrival_message": record["arrival_message"],
                    "wait_seconds": record["wait_seconds"],
                    "return_to_base": record["return_to_base"],
                }
                for record in records
            ],
        }
        self.export_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.export_path.with_suffix(".tmp")
        temporary_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary_path.replace(self.export_path)
        return self.export_path

    def interpret(self, request: str) -> dict[str, Any]:
        normalized_request = normalize(request)
        candidates: list[tuple[int, dict[str, Any], str]] = []
        for destination in self.list():
            variants = [destination["name"], *destination["aliases"], *destination["phrases"]]
            for variant in variants:
                normalized_variant = normalize(variant)
                if normalized_variant and normalized_variant in normalized_request:
                    candidates.append((len(normalized_variant), destination, variant))
        if not candidates:
            return {
                "recognized": False,
                "request": request,
                "message": "Nenhum destino foi encontrado para essa frase.",
            }
        _, destination, matched_phrase = max(candidates, key=lambda item: item[0])
        return {
            "recognized": True,
            "request": request,
            "matched_phrase": matched_phrase,
            "destination": destination,
            "message": f"Destino reconhecido: {destination['name']}.",
        }

    def simulate(self, request: str) -> dict[str, Any]:
        interpretation = self.interpret(request)
        if not interpretation["recognized"]:
            return {**interpretation, "events": []}
        destination = interpretation["destination"]
        events = [
            {"state": "pedido reconhecido", "detail": f"Destino: {destination['name']}"},
            {"state": "resposta", "detail": f"Me siga, por favor. Vou até {destination['name']}."},
            {"state": "navegação simulada", "detail": "Nenhum motor será acionado neste modo."},
            {"state": "chegada", "detail": destination["arrival_message"]},
            {"state": "espera", "detail": f"{destination['wait_seconds']:g} segundos"},
        ]
        if destination["return_to_base"]:
            home = next((item for item in self.list() if item["is_home"]), None)
            if home:
                events.append({"state": "retorno", "detail": f"Retornar para a base: {home['name']}"})
        return {**interpretation, "events": events}
