"""Carga de configuración (config/lab.yaml + config/configs/*.yaml + variables de entorno)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"


def _load_yaml(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


@dataclass
class LabSettings:
    raw: dict[str, Any]
    root: Path = ROOT

    @property
    def model(self) -> dict[str, Any]:
        m = dict(self.raw["model"])
        m["name"] = os.getenv("TFM_MODEL", m["name"])
        m["host"] = os.getenv("OLLAMA_HOST", m["host"])
        return m

    @property
    def agent(self) -> dict[str, Any]:
        return self.raw["agent"]

    @property
    def guards(self) -> dict[str, Any]:
        g = dict(self.raw["guards"])
        g["input_backend"] = os.getenv("TFM_GUARD_BACKEND", g["input_backend"])
        g["input_model"] = os.getenv("TFM_GUARD_MODEL", g["input_model"])
        return g

    @property
    def trusted_hosts(self) -> list[str]:
        return list(self.raw.get("trusted_hosts", []))

    def path(self, key: str) -> Path:
        p = Path(self.raw["paths"][key])
        return p if p.is_absolute() else self.root / p

    @property
    def policy(self) -> dict[str, Any]:
        return _load_yaml(self.path("policy"))


@dataclass
class RunConfig:
    name: str
    description: str
    controls: dict[str, bool] = field(default_factory=dict)

    def on(self, control: str) -> bool:
        return bool(self.controls.get(control, False))


def load_settings(path: Path | None = None) -> LabSettings:
    return LabSettings(_load_yaml(path or CONFIG_DIR / "lab.yaml"))


def load_run_config(name: str) -> RunConfig:
    data = _load_yaml(CONFIG_DIR / "configs" / f"{name.lower()}.yaml")
    return RunConfig(name=data["name"], description=data.get("description", ""), controls=data["controls"])


def all_run_configs() -> list[str]:
    return sorted(p.stem.upper() for p in (CONFIG_DIR / "configs").glob("c*.yaml"))
