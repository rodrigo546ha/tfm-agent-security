"""Orquestador de la campaña: configuración (C0/C1/C2) × escenario × variante + 50 tareas benignas.

Salidas en results/: runs.jsonl (una fila por intento), summary.csv y telemetry.jsonl.
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
from tfm_lab.llm import LLMBackend, ScriptedBackend, build_backend
from tfm_lab.settings import LabSettings, load_run_config, load_settings
from tfm_lab.telemetry import Telemetry
from tfm_lab.tools.builtin import build_registry

KNOWN_SECRET_KEYS = ("secrets.clave_api_crm", "secrets.clave_firma", "vault.crm")


def split_corpus(settings: LabSettings) -> tuple[list[str], list[str]]:
    """Separa contratos con carga (marcador en comentario HTML) de los limpios."""
    poisoned, clean = [], []
    for p in sorted(settings.path("contracts").glob("CT-*.md")):
        (poisoned if "<!--" in p.read_text(encoding="utf-8") else clean).append(p.stem)
    return poisoned, clean


def variants(scenario: Scenario, settings: LabSettings) -> list[dict[str, Any]]:
    if scenario.vector == "document":
        poisoned, _ = split_corpus(settings)
        return [{"id": f"S2-{cid}", "mutator": "corpus", "prompt": scenario.task_template.format(doc_id=cid),
                 "tool_desc": None} for cid in poisoned]
    out = []
    for si, seed in enumerate(scenario.seeds):
        for mut in scenario.mutators:
            payload = mutators.apply(mut, seed)
            if scenario.vector == "tool_description":
                out.append({"id": f"{scenario.id}-s{si}-{mut}", "mutator": mut,
                            "prompt": scenario.task_template, "tool_desc": payload})
            else:
                out.append({"id": f"{scenario.id}-s{si}-{mut}", "mutator": mut,
                            "prompt": scenario.task_template.format(payload=payload), "tool_desc": None})
    return out


def _agent(llm: LLMBackend, settings: LabSettings, cfg_name: str, tel: Telemetry,
           extra_tools: list[dict[str, Any]] | None = None):
    cfg = load_run_config(cfg_name)
    # El broker de credenciales forma parte del motor de políticas (C2). En C0/C1 el secreto sale en claro.
    ctx = build_context(settings, broker=cfg.on("policy"))
    known = [resolve_canary(ctx.canaries, k) for k in KNOWN_SECRET_KEYS]
    controls = ControlSet(cfg, settings, known_secrets=known)
    reg = controls.register_tools(build_registry(extra_tools=extra_tools))
    return Agent(llm, reg, controls, ctx, max_steps=settings.agent["max_steps"], telemetry=tel), ctx


def run_attack(llm, settings, cfg_name: str, scenario: Scenario, v: dict[str, Any], tel: Telemetry) -> dict:
    extra = [{"name": scenario.extra_tool, "description": v["tool_desc"]}] if v["tool_desc"] else None
    agent, ctx = _agent(llm, settings, cfg_name, tel, extra)
    r = agent.run(v["prompt"])
    j = judge(scenario, r, ctx)
    return {
        "kind": "attack", "config": cfg_name, "scenario": scenario.id, "variant": v["id"], "mutator": v["mutator"],
        "attack_success": j.success, "signals": j.signals, "canaries_leaked": j.canaries_leaked,
        "forbidden_executed": j.forbidden_executed, "untrusted_egress": j.untrusted_egress,
        "blocked_input": r.blocked_input, "denied_tool": r.any_denied, "sanitized_result": r.any_sanitized,
        "rejected_tools": list(r.rejected_tools), "output_findings": r.output_findings,
        "tools_called": [c.name for c in r.tool_calls], "steps": r.steps, "latency_s": r.latency_s,
        "error": r.error,
    }


def run_benign(llm, settings, cfg_name: str, task: str, idx: int, tel: Telemetry) -> dict:
    agent, _ = _agent(llm, settings, cfg_name, tel)
    r = agent.run(task)
    blocked = r.blocked_input or r.any_denied or r.any_sanitized
    return {"kind": "benign", "config": cfg_name, "scenario": "BENIGN", "variant": f"B-{idx:02d}", "mutator": "-",
            "benign_blocked": blocked, "blocked_input": r.blocked_input, "denied_tool": r.any_denied,
            "sanitized_result": r.any_sanitized, "tools_called": [c.name for c in r.tool_calls],
            "steps": r.steps, "latency_s": r.latency_s, "error": r.error}


class PreflightError(RuntimeError):
    pass


def preflight(settings: LabSettings, configs: list[str]) -> str:
    """Comprueba Ollama, el modelo y el guardrail ANTES de lanzar nada. Devuelve un resumen."""
    m = settings.model
    try:
        from ollama import Client
        names = {x.model for x in Client(host=m["host"]).list().models}
    except Exception as exc:  # noqa: BLE001
        raise PreflightError(
            f"No hay conexión con Ollama en {m['host']} ({type(exc).__name__}). "
            "Instala Ollama (https://ollama.com/download), ábrelo y vuelve a intentarlo.") from exc
    if m["name"] not in names and f"{m['name']}:latest" not in names:
        raise PreflightError(f"El modelo '{m['name']}' no está descargado. Ejecuta: ollama pull {m['name']}")
    needs_guard = any(load_run_config(c).on("input_guard") or load_run_config(c).on("tool_result_guard")
                      for c in configs)
    g = settings.guards
    if needs_guard:
        from tfm_lab.controls.input_guard import get_classifier
        try:
            get_classifier(g["input_backend"], g["input_model"], g["input_threshold"])  # descarga/carga una vez
        except RuntimeError as exc:
            raise PreflightError(str(exc)) from exc
    return f"Ollama OK · modelo {m['name']} · guardrail {g['input_model'] if needs_guard else 'no requerido'}"


def run_campaign(configs: list[str] | None = None, scenarios: list[str] | None = None,
                 benign: bool = True, dry_run: bool = False, n_benign: int = 50) -> Path:
    settings = load_settings()
    results = settings.path("results")
    results.mkdir(parents=True, exist_ok=True)
    runs_path = results / "runs.jsonl"
    runs_path.write_text("", encoding="utf-8")
    tel = Telemetry(results / "telemetry.jsonl", run_id="campaign")

    cfgs = configs or ["C0", "C1", "C2"]
    if not dry_run:
        print(preflight(settings, cfgs))
    llm: LLMBackend = (ScriptedBackend([{"content": "Hecho.", "tool_calls": []}]) if dry_run
                       else build_backend(settings.model))
    scens = [s for s in SCENARIOS if not scenarios or s.id in scenarios]
    _, clean = split_corpus(settings)
    tasks = benign_tasks(n_benign, clean)
    plan = {s.id: len(variants(s, settings)) for s in scens}
    print(f"Modelo: {llm.name} · variantes por escenario: {plan} · benignas: {len(tasks) if benign else 0}")

    rows: list[dict[str, Any]] = []
    t0 = time.time()
    with open(runs_path, "a", encoding="utf-8") as fh:
        streak = 0

        def _write(row: dict) -> None:
            nonlocal streak
            if row.get("error"):
                # Un error del modelo NO es un ataque fallido: se marca y se excluye de las métricas.
                row["attack_success"] = None
                streak += 1
            else:
                streak = 0
            rows.append(row)
            fh.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
            fh.flush()
            if streak >= 3:
                raise RuntimeError(f"3 errores seguidos del agente; último: {row['error']}. Campaña abortada.")

        for cfg_name in cfgs:
            for s in scens:
                for v in variants(s, settings):
                    _write(run_attack(llm, settings, cfg_name, s, v, tel.child(f"{cfg_name}:{v['id']}")))
                    last = rows[-1]
                    estado = f"ERROR {last['error'][:60]}" if last.get("error") else f"éxito={last['attack_success']}"
                    print(f"  {cfg_name} {v['id']:<28} {estado}", flush=True)
            if benign:
                for i, task in enumerate(tasks):
                    _write(run_benign(llm, settings, cfg_name, task, i, tel.child(f"{cfg_name}:B-{i:02d}")))

    _write_summary(rows, results / "summary.csv")
    print(f"Campaña completada en {time.time() - t0:.0f}s · {len(rows)} filas -> {runs_path}")
    return runs_path


def _write_summary(rows: list[dict[str, Any]], path: Path) -> None:
    keys = ["kind", "config", "scenario", "variant", "mutator", "attack_success", "benign_blocked", "signals",
            "blocked_input", "denied_tool", "sanitized_result", "forbidden_executed", "untrusted_egress",
            "steps", "latency_s", "error"]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
