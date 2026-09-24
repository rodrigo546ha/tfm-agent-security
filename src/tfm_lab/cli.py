"""CLI del laboratorio: `tfm-lab <comando>`."""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="tfm-lab", description="Laboratorio TFM: seguridad de agentes LLM")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("data", help="Genera el corpus sintético (CRM, contratos, canarios).")
    sub.add_parser("manifest", help="Genera el manifiesto de integridad de herramientas.")

    pc = sub.add_parser("campaign", help="Ejecuta la campaña experimental.")
    pc.add_argument("--configs", nargs="*", default=None, help="C0 C1 C2 (por defecto las tres)")
    pc.add_argument("--scenarios", nargs="*", default=None, help="S1 S2 S3 S4")
    pc.add_argument("--no-benign", action="store_true")
    pc.add_argument("--dry-run", action="store_true", help="Sin modelo (backend scripted): valida el pipeline.")

    sub.add_parser("report", help="Genera tablas y gráficas de ASR desde results/.")

    pt = sub.add_parser("chat", help="Chat manual con el agente en una configuración.")
    pt.add_argument("--config", default="C2")
    pt.add_argument("message")

    args = p.parse_args(argv)

    if args.cmd == "data":
        from tfm_lab.data.generate import main as gen
        gen()
    elif args.cmd == "manifest":
        from pathlib import Path

        from tfm_lab.settings import load_settings
        from tfm_lab.tools import write_manifest
        from tfm_lab.tools.builtin import build_registry
        s = load_settings()
        path = Path(s.path("tool_manifest"))
        write_manifest(build_registry(), path)
        print(f"Manifiesto -> {path}")
    elif args.cmd == "campaign":
        from tfm_lab.eval.campaign import run_campaign
        run_campaign(configs=args.configs, scenarios=args.scenarios,
                     benign=not args.no_benign, dry_run=args.dry_run)
    elif args.cmd == "report":
        from tfm_lab.eval.report import main as rep
        rep()
    elif args.cmd == "chat":
        _chat(args.config, args.message)
    return 0


def _chat(cfg_name: str, message: str) -> None:
    from tfm_lab.agent import Agent
    from tfm_lab.controls import ControlSet
    from tfm_lab.lab import build_context
    from tfm_lab.llm import build_backend
    from tfm_lab.settings import load_run_config, load_settings
    from tfm_lab.tools.builtin import build_registry

    s = load_settings()
    cfg = load_run_config(cfg_name)
    ctx = build_context(s, broker=True)
    controls = ControlSet(cfg, s, known_secrets=[])
    reg = controls.register_tools(build_registry())
    agent = Agent(build_backend(s.model), reg, controls, ctx, max_steps=s.agent["max_steps"])
    res = agent.run(message)
    print(res.final)
    for c in res.tool_calls:
        flag = "OK " if c.allowed else "DEN"
        print(f"  [{flag}] {c.name}({c.arguments}) {c.reason}")


if __name__ == "__main__":
    sys.exit(main())
