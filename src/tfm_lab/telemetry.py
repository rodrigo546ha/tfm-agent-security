"""Telemetría estructurada (JSONL). Cada evento lleva run_id para reconstruir la traza completa.

El formato está pensado para poder escribir reglas de detección (p. ej. Sigma) sobre él más adelante.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class Telemetry:
    def __init__(self, path: Path | None = None, run_id: str = "adhoc") -> None:
        self.path = path
        self.run_id = run_id
        self.events: list[dict[str, Any]] = []
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, event: str, **fields: Any) -> dict[str, Any]:
        rec = {"ts": round(time.time(), 3), "run_id": self.run_id, "event": event, **fields}
        self.events.append(rec)
        if self.path:
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
        return rec

    def child(self, run_id: str) -> Telemetry:
        return Telemetry(self.path, run_id)
