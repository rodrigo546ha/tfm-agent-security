"""Registro de herramientas del agente."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]
    func: Callable[..., Any]
    egress: bool = False  # saca datos del perímetro (http_fetch, enviar_email)
    sensitive: bool = False  # devuelve datos sensibles
    origin: str = "builtin"  # builtin | third_party (p. ej. un servidor MCP externo)

    def schema(self) -> dict[str, Any]:
        return {"type": "function",
                "function": {"name": self.name, "description": self.description, "parameters": self.parameters}}

    def fingerprint(self) -> str:
        blob = json.dumps({"n": self.name, "d": self.description, "p": self.parameters}, sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()


@dataclass
class ToolRegistry:
    tools: dict[str, ToolSpec] = field(default_factory=dict)
    rejected: dict[str, str] = field(default_factory=dict)

    def add(self, spec: ToolSpec) -> None:
        self.tools[spec.name] = spec

    def remove(self, name: str, reason: str) -> None:
        self.tools.pop(name, None)
        self.rejected[name] = reason

    def schemas(self) -> list[dict[str, Any]]:
        return [t.schema() for t in self.tools.values()]

    def get(self, name: str) -> ToolSpec | None:
        return self.tools.get(name)

    def execute(self, name: str, args: dict[str, Any], ctx: Any) -> Any:
        spec = self.tools.get(name)
        if spec is None:
            return {"error": f"herramienta '{name}' no disponible"}
        try:
            return spec.func(ctx, **args)
        except TypeError as exc:
            return {"error": f"argumentos inválidos para {name}: {exc}"}
        except Exception as exc:  # noqa: BLE001 - el agente debe ver el error, no romper la campaña
            return {"error": f"{type(exc).__name__}: {exc}"}


def write_manifest(registry: ToolRegistry, path: Path) -> None:
    """Genera el manifiesto de integridad (hash de cada descripción aprobada)."""
    data = {name: spec.fingerprint() for name, spec in sorted(registry.tools.items())}
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def load_manifest(path: Path) -> dict[str, str]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
