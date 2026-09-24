"""Entorno simulado del laboratorio: gateway de egress (sumidero), vault de credenciales y contexto por ejecución.

Nada sale a Internet: toda petición http_fetch / enviar_email queda capturada en el sumidero y, si existe,
se responde con un fixture de data/web/<host>/<ruta>.
"""

from __future__ import annotations

import json
import re
import secrets as pysecrets
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

CANARY_RE = re.compile(r"CANARY-[A-Z]+-[0-9A-F]{8}")
HANDLE_RE = re.compile(r"cred://([a-z0-9_-]+)/([0-9a-f]{8})")


def host_of(url: str) -> str:
    return (urlparse(url if "://" in url else f"http://{url}").hostname or "").lower()


def host_matches(host: str, domains: list[str]) -> bool:
    return any(host == d or host.endswith("." + d) for d in domains)


@dataclass
class Capture:
    kind: str  # http | email
    destination: str  # url o destinatario
    host: str
    payload: str
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


class Vault:
    """Emisor de credenciales. Con broker=True devuelve handles; con broker=False, el secreto en claro."""

    def __init__(self, secrets_by_service: dict[str, str], broker: bool = False, ttl: int = 300,
                 allowed_destinations: dict[str, list[str]] | None = None):
        self.secrets = secrets_by_service
        self.broker = broker
        self.ttl = ttl
        self.allowed = allowed_destinations or {}
        self._handles: dict[str, tuple[str, float]] = {}

    def issue(self, service: str) -> str:
        if service not in self.secrets:
            return f"ERROR: servicio desconocido '{service}'"
        if not self.broker:
            return self.secrets[service]
        hid = pysecrets.token_hex(4)
        self._handles[hid] = (service, time.time() + self.ttl)
        return f"cred://{service}/{hid}"

    def resolve_for(self, text: str, host: str) -> tuple[str, list[str]]:
        """Sustituye handles por el secreto solo si el host destino está autorizado para ese servicio."""
        denied: list[str] = []

        def _sub(m: re.Match[str]) -> str:
            service, hid = m.group(1), m.group(2)
            entry = self._handles.get(hid)
            if not entry or entry[1] < time.time() or entry[0] != service:
                denied.append(f"handle inválido o caducado ({service})")
                return "[CREDENCIAL-INVÁLIDA]"
            if not host_matches(host, self.allowed.get(service, [])):
                denied.append(f"destino {host} no autorizado para {service}")
                return "[CREDENCIAL-DENEGADA]"
            return self.secrets[service]

        return HANDLE_RE.sub(_sub, text), denied


class EgressGateway:
    """Sumidero de egress. Registra todo lo que el agente intenta sacar y sirve fixtures web locales."""

    def __init__(self, web_dir: Path, vault: Vault, log_path: Path | None = None):
        self.web_dir = web_dir
        self.vault = vault
        self.log_path = log_path
        self.captures: list[Capture] = []

    def _record(self, cap: Capture) -> None:
        self.captures.append(cap)
        if self.log_path:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(cap.to_dict(), ensure_ascii=False) + "\n")

    def fetch(self, url: str, body: str = "") -> str:
        host = host_of(url)
        resolved_url, _ = self.vault.resolve_for(url, host)
        resolved_body, _ = self.vault.resolve_for(body, host)
        self._record(Capture("http", resolved_url, host, resolved_body))
        parsed = urlparse(url if "://" in url else f"http://{url}")
        path = parsed.path.strip("/") or "index"
        for candidate in (self.web_dir / host / path, self.web_dir / host / f"{path}.html",
                          self.web_dir / host / f"{path}.md"):
            if candidate.is_file():
                return candidate.read_text(encoding="utf-8")
        return f"HTTP 200 OK ({host}): recurso sin contenido."

    def send_email(self, to: str, subject: str, body: str) -> str:
        host = to.split("@")[-1].lower() if "@" in to else ""
        resolved, _ = self.vault.resolve_for(f"{subject}\n{body}", host)
        self._record(Capture("email", to, host, resolved))
        return f"Email enviado a {to}."


@dataclass
class LabContext:
    db_path: Path
    contracts_dir: Path
    gateway: EgressGateway
    vault: Vault
    canaries: dict[str, Any]
    trusted_hosts: list[str]
    policy: dict[str, Any] = field(default_factory=dict)

    def db(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con

    def is_untrusted(self, host: str) -> bool:
        return not host_matches(host, self.trusted_hosts)


def build_context(settings: Any, broker: bool, log_path: Path | None = None) -> LabContext:
    canaries_path = settings.path("canaries")
    if not canaries_path.exists():
        raise FileNotFoundError(f"No existe {canaries_path}. Ejecuta `make data` primero.")
    canaries = json.loads(canaries_path.read_text(encoding="utf-8"))
    policy = settings.policy
    cred = policy.get("credentials", {})
    vault = Vault(
        canaries["vault"],
        broker=broker and cred.get("broker", True),
        ttl=cred.get("ttl_seconds", 300),
        allowed_destinations=cred.get("allowed_destinations", {}),
    )
    gateway = EgressGateway(settings.path("web"), vault, log_path)
    return LabContext(
        db_path=settings.path("db"),
        contracts_dir=settings.path("contracts"),
        gateway=gateway,
        vault=vault,
        canaries=canaries,
        trusted_hosts=settings.trusted_hosts,
        policy=policy,
    )
