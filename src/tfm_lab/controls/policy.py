"""Motor de políticas de herramientas (C2): mínimo privilegio, egress, HITL y datos sensibles en argumentos."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tfm_lab.controls.output_filter import OutputFilter
from tfm_lab.lab import host_matches, host_of


@dataclass
class Decision:
    allowed: bool
    reason: str = ""
    control: str = ""
    hitl: bool = False


class PolicyEngine:
    def __init__(self, policy: dict[str, Any], role: str, dlp: OutputFilter) -> None:
        self.p = policy
        self.role = policy["roles"][role]
        self.dlp = dlp

    def authorize(self, name: str, args: dict[str, Any]) -> Decision:
        if name not in self.role.get("tools", []):
            return Decision(False, f"'{name}' fuera de la allowlist del rol", "least_privilege")

        text_args = " ".join(str(v) for v in args.values())
        if name == "http_fetch":
            host = host_of(str(args.get("url", "")))
            if not host_matches(host, self.p["egress"]["allow_domains"]):
                return Decision(False, f"destino {host} fuera de la allowlist de egress", "egress_allowlist")
        if name in ("http_fetch", "enviar_email"):
            scan = self.dlp.scan(text_args)
            if scan.hit:
                return Decision(False, f"datos sensibles en argumentos: {sorted(set(scan.findings))}", "dlp_args")
        if name == "enviar_email":
            dom = str(args.get("destinatario", "")).split("@")[-1].lower()
            if not host_matches(dom, self.p["email"]["allow_recipient_domains"]):
                return Decision(False, f"destinatario @{dom} no permitido", "egress_allowlist")
        if name in self.p.get("hitl", {}).get("tools", []):
            return self._approve(name, args)
        return Decision(True)

    def _approve(self, name: str, args: dict[str, Any]) -> Decision:
        """Aprobador humano simulado. 'strict': aprueba solo lo que ya ha superado los controles anteriores
        y no contiene handles de credencial. En la demo manual se puede cambiar a 'ask' (input())."""
        mode = self.p["hitl"].get("approver", "strict")
        if mode == "ask":  # pragma: no cover - interactivo
            ok = input(f"[HITL] ¿Aprobar {name}({args})? [s/N] ").strip().lower() == "s"
            return Decision(ok, "" if ok else "denegado por el operador", "hitl", True)
        if "cred://" in " ".join(str(v) for v in args.values()):
            return Decision(False, "HITL: el mensaje contiene una credencial", "hitl", True)
        return Decision(True, "aprobado por HITL (auto)", "hitl", True)

    def mask(self, name: str, result: Any) -> Any:
        fields = self.role.get("mask_fields", {}).get(name, [])
        if isinstance(result, dict) and fields:
            return {k: ("***" if k in fields else v) for k, v in result.items()}
        return result
