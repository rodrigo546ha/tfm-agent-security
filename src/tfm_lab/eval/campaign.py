"""Orquestador de la campaña experimental: para cada configuración (C0/C1/C2), escenario y variante,
ejecuta el agente y registra el veredicto. Produce results/runs.jsonl y results/summary.csv.
"""

from __future__ import annotations

import csv
import json
import time
from pathlib import Path
from typing import Any

from tfm_lab.agent import Agent
from tfm_lab.attacks import mutators
from tfm_lab.attacks.scenarios import SCENARIOS, Scenario, resolve_canary
from tfm_lab.controls import ControlSet
from tfm_lab.eval.benign import benign_tasks
from tfm_lab.eval.detector import judge
from tfm_lab.lab import build_context
from tfm_lab.llm import LLMBackend, build_backend
from tfm_lab.settings import LabSettings, load_run_config, load_settings
from tfm_lab.telemetry import Telemetry
from tfm_lab.tools.builtin import build_registry


def _variants(scenario: Scenario) -> list[tuple[str, str, str]]:
    """Devuelve (variant_id, mutator, payload_base) por cada semilla × mutador."""
    out = []
    for si, seed in enumerate(scenario.seeds):
        for mut in scenario.mutators:
            out.append((f"{scenario.id}-s{si}-{mut}", mut, seed))
    return out


def _build_prompt(scenario: Scenario, mut: str, seed: str, settings: LabSettings) -> tuple[str, str]:
    """Construye el mensaje de usuario y prepara el vector (documento/web) si aplica. Devuelve (msg, doc_id)."""
    payload = mutators.apply(mut, seed)
    if scenario.vector == "user":
        return scenario.task_template.format(payload=payload), ""
    if scenario.vector == "document":
        # Escribe un contrato temporal con la carga y pide resumirlo.
        doc_id = f"CT-INJ-{mut}"
        path = settings.path("contracts") / f"{doc_id}.md"
        path.write_text(f"# Contrato {doc_id}\n\n**Importe:** 42000 EUR\n\n<!-- asistente: {payload} -->\n",
                        encoding="utf-8")
        return scenario.task_template.format(doc_id=doc_id), doc_id
    # tool_description: la carga va en la descripción de la herramienta (se inyecta al construir el registro)
    return scenario.task_template, ""


def run_one(llm: LLMBackend, settings: LabSettings, cfg_name: str, scenario: Scenario, mut: str,
            seed: str, tel: Telemetry) -> dict[str, Any]:
    cfg = load_run_config(cfg_name)
    # El broker de credenciales es un control de C2 (policy). En C0/C1 el vault entrega el secreto en claro.
    ctx = build_context(settings, broker=cfg.on("policy"), log_path=None)
    known = [resolve_canary(ctx.canaries, k) for k in
             ("secrets.clave_api_crm", "secrets.clave_firma", "vault.crm")]
    controls = ControlSet(cfg, settings, known_secrets=known)

    extra = []
    for t in scenario.extra_tools:
        extra.append({"name": t["name"], "description": mutators.apply(mut, seed)})
    reg = controls.register_tools(build_registry(extra_tools=extra))

    msg, _ = _build_prompt(scenario, mut, seed, settings)
    agent = Agent(llm, reg, controls, ctx, max_steps=settings.agent["max_steps"], telemetry=tel)
    result = agent.run(msg)

    egress_text = "\n".join(c.payload for c in ctx.gateway.captures)
    j = judge(scenario, result, ctx.canaries, egress_text)
    return {
        "config": cfg_name, "scenario": scenario.id, "mutator": mut,
        "attack_success": j.success, "leaked_where": j.where, "forbidden_executed": j.forbidden_executed,
        "blocked_input": result.blocked_input, "denied_tool": result.any_denied,
        "sanitized_result": result.any_sanitized, "output_findings": result.output_findings,
        "rejected_tools": list(result.rejected_tools), "steps": result.steps,
        "latency_s": result.latency_s, "error": result.error,
    }


def run_benign(llm: LLMBackend, settings: LabSettings, cfg_name: str, tel: Telemetry,
               n: int = 50) -> dict[str, Any]:
    cfg = load_run_config(cfg_name)
    known = []
    blocked = 0
    tasks = benign_tasks(n)
    for task in tasks:
        ctx = build_context(settings, broker=cfg.on("policy"))
        controls = ControlSet(cfg, settings, known_secrets=known)
        reg = controls.register_tools(build_registry())
        agent = Agent(llm, reg, controls, ctx, max_steps=settings.agent["max_steps"], telemetry=tel)
        r = agent.run(task)
        if r.blocked_input or r.any_denied:
            blocked += 1
    return {"config": cfg_name, "benign_n": len(tasks), "benign_blocked": blocked,
            "false_block_rate": round(blocked / len(tasks), 4)}


def run_campaign(configs: list[str] | None = None, scenarios: list[str] | None = None,
                 benign: bool = True, dry_run: bool = False) -> Path:
    settings = load_settings()
    results_dir = settings.path("results")
    results_dir.mkdir(parents=True, exist_ok=True)
    runs_path = results_dir / "runs.jsonl"
    tel = Telemetry(results_dir / "telemetry.jsonl", run_id="campaign")
    runs_path.write_text("", encoding="utf-8")

    if dry_run:
        from tfm_lab.llm import ScriptedBackend
        llm: LLMBackend = ScriptedBackend([{"content": "Hecho.", "tool_calls": []}])
    else:
        llm = build_backend(settings.model)

    cfgs = configs or ["C0", "C1", "C2"]
    scens = [s for s in SCENARIOS if not scenarios or s.id in scenarios]
    rows: list[dict[str, Any]] = []
    t0 = time.time()

    with open(runs_path, "a", encoding="utf-8") as fh:
        for cfg_name in cfgs:
            for scenario in scens:
                for _vid, mut, seed in _variants(scenario):
                    row = run_one(llm, settings, cfg_name, scenario, mut, seed,
                                  tel.child(f"{cfg_name}-{scenario.id}-{mut}"))
                    rows.append(row)
                    fh.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
            if benign:
                b = run_benign(llm, settings, cfg_name, tel.child(f"{cfg_name}-benign"))
                b.update({"scenario": "BENIGN", "mutator": "-"})
                rows.append(b)
                fh.write(json.dumps(b, ensure_ascii=False) + "\n")

    _write_summary(rows, results_dir / "summary.csv")
    print(f"Campaña completada en {time.time() - t0:.1f}s. {len(rows)} filas -> {runs_path}")
    return runs_path


def _write_summary(rows: list[dict[str, Any]], path: Path) -> None:
    keys = ["config", "scenario", "mutator", "attack_success", "blocked_input", "denied_tool",
            "sanitized_result", "forbidden_executed", "steps", "latency_s",
            "benign_n", "benign_blocked", "false_block_rate", "error"]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
