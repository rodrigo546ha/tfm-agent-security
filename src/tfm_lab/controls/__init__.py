"""ControlSet: compone los controles activos según la configuración (C0/C1/C2)."""

from __future__ import annotations

import json
from typing import Any

from tfm_lab.controls.input_guard import GuardVerdict, InputGuard, get_classifier
from tfm_lab.controls.output_filter import OutputFilter
from tfm_lab.controls.policy import Decision, PolicyEngine
from tfm_lab.settings import LabSettings, RunConfig
from tfm_lab.tools import ToolRegistry, load_manifest

BLOCK_MSG = "Lo siento, no puedo procesar esta petición: ha sido bloqueada por la política de seguridad."
SANITIZED = "[CONTENIDO BLOQUEADO POR EL GUARDRAIL: posible inyección de instrucciones en el resultado]"


class ControlSet:
    def __init__(self, cfg: RunConfig, settings: LabSettings, known_secrets: list[str],
                 classifier: Any | None = None) -> None:
        self.cfg = cfg
        g = settings.guards
        needs_guard = cfg.on("input_guard") or cfg.on("tool_result_guard")
        clf = classifier or (get_classifier(g["input_backend"], g["input_model"], g["input_threshold"])
                             if needs_guard else None)
        self.guard = InputGuard(clf) if clf else None
        self.dlp = OutputFilter(known_secrets)
        self.policy = (PolicyEngine(settings.policy, settings.agent["role"], self.dlp)
                       if cfg.on("policy") else None)
        self.manifest = load_manifest(settings.path("tool_manifest")) if cfg.on("policy") else {}

    # -- registro de herramientas ----------------------------------------------------------------------------
    def register_tools(self, reg: ToolRegistry) -> ToolRegistry:
        for name, spec in list(reg.tools.items()):
            if self.policy and self.policy.p.get("tool_integrity", {}).get("enforce_manifest"):
                if self.manifest.get(name) != spec.fingerprint():
                    reg.remove(name, "descripción no coincide con el manifiesto (pinning)")
                    continue
            if self.guard and self.cfg.on("tool_result_guard") and spec.origin == "third_party":
                v = self.guard.check(spec.description, source=f"tool_description:{name}")
                if v.blocked:
                    reg.remove(name, f"descripción marcada por guardrail ({v.reason})")
        return reg

    # -- puntos de control del bucle -----------------------------------------------------------------------
    def check_user_input(self, text: str) -> GuardVerdict | None:
        if self.guard and self.cfg.on("input_guard"):
            return self.guard.check(text, "user")
        return None

    def authorize(self, name: str, args: dict[str, Any]) -> Decision:
        return self.policy.authorize(name, args) if self.policy else Decision(True)

    def process_tool_result(self, name: str, result: Any) -> tuple[str, GuardVerdict | None]:
        if self.policy:
            result = self.policy.mask(name, result)
        text = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
        verdict = None
        if self.guard and self.cfg.on("tool_result_guard"):
            verdict = self.guard.check(text, f"tool_result:{name}")
            if verdict.blocked:
                return SANITIZED, verdict
        return text, verdict

    def filter_output(self, text: str) -> tuple[str, list[str]]:
        if self.cfg.on("output_filter"):
            r = self.dlp.scan(text)
            return r.text, r.findings
        return text, []
