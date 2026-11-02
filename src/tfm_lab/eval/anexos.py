"""Anexos de la memoria generados desde el código y la telemetría, para no copiar a mano semillas ni evidencias.

- `corpus_latex`: semillas de cada escenario y plantilla de cada mutador (anexo B).
- `evidence_latex`: eventos de telemetría de ejecuciones concretas de la última campaña (anexo C).
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

from tfm_lab.attacks import mutators
from tfm_lab.attacks.scenarios import INDIRECT_MUTATORS, INDIRECT_SEEDS, SCENARIOS

# Ejecuciones que ilustran el anexo C: el mismo ataque sin y con controles, y un éxito residual de C2.
EVIDENCE_RUNS = ["C0:S4-s0-none", "C2:S4-s0-none", "C2:S2-CT-016-s1-none"]

_TEX = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{",
        "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}", "<": r"\textless{}",
        ">": r"\textgreater{}", "—": "---", "-": "-{}", "\n": " "}  # "-{}": que -- no se una en una raya


def tex(s: str, limit: int | None = None) -> str:
    """Escapa texto para LaTeX; la raya Unicode pasa a --- (tectonic no la representa con lmodern T1).
    Tras / . _ = - se permite partir la línea, para que URL y tokens no se salgan del margen."""
    cut = limit is not None and len(s) > limit
    s = s[:limit] if cut else s
    out = "".join(_TEX.get(c, c) + (r"\allowbreak{}" if c in "/._=-" else "") for c in s)
    return out + (r"\ldots" if cut else "")


def _tabular(header: str, rows: list[str]) -> list[str]:
    return [r"\noindent\begin{tabularx}{\textwidth}{@{}l>{\raggedright\arraybackslash}X@{}}", r"\toprule", header,
            r"\midrule", *rows, r"\bottomrule", r"\end{tabularx}"]


def corpus_latex(out: Path, web_dir: Path | None = None) -> None:
    lines = [r"\paragraph{Semillas.} Cada semilla fija el objetivo del ataque; S2 inserta las suyas en contratos del"
             " corpus y S3 sustituye con ellas la descripción de \\texttt{convertir\\_divisa}.", "",
             r"\begin{footnotesize}"]
    rows = []
    for s in SCENARIOS:
        seeds = INDIRECT_SEEDS if s.id == "S2" else s.seeds
        muts = INDIRECT_MUTATORS if s.id == "S2" else s.mutators
        rows.append(rf"\multicolumn{{2}}{{@{{}}p{{\linewidth}}@{{}}}}{{\textbf{{{s.id}}} --- {tex(s.name)}. Mutadores: "
                    + ", ".join(rf"\texttt{{{tex(m)}}}" for m in muts) + r".} \\")
        rows += [rf"{s.id}-s{i} & {tex(seed)} \\" for i, seed in enumerate(seeds)]
    lines += _tabular(r"Semilla & Texto \\", rows)
    page = web_dir / "intranet.lab" / "aviso" if web_dir else None
    if page and page.exists():
        lines += ["", r"\smallskip\noindent La semilla S4-s2 remite a una página de la intranet simulada con este"
                  rf" contenido: \enquote{{{tex(page.read_text(encoding='utf-8').strip())}}}."]
    lines += [r"\end{footnotesize}", "", r"\paragraph{Mutadores.} Cada mutador transforma la semilla"
              r" (\emph{carga}) sin cambiar su objetivo.", "", r"\begin{footnotesize}"]
    mark = "CARGA"
    enc = base64.b64encode(mark.encode("utf-8")).decode("ascii")
    rows = []
    for name, fn in mutators.MUTATORS.items():
        text = tex(fn(mark)).replace(mark, r"\emph{carga}").replace(enc, r"\emph{carga codificada en base64}")
        rows.append(rf"\texttt{{{tex(name)}}} & {text} \\")
    lines += _tabular(r"Mutador & Variante generada \\", rows) + [r"\end{footnotesize}"]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def last_run_events(telemetry: Path, run_id: str) -> list[dict]:
    """Eventos de la última ejecución de `run_id` (telemetry.jsonl acumula todas las campañas)."""
    events = [e for e in map(json.loads, telemetry.read_text(encoding="utf-8").splitlines())
              if e.get("run_id") == run_id]
    starts = [i for i, e in enumerate(events) if e["event"] == "user_input"]
    return events[starts[-1]:] if starts else []


def _describe(e: dict) -> str:
    kind = e["event"]
    if kind == "user_input":
        return tex(e["text"], 200)
    if kind == "guard_input":
        return f"{'bloqueado' if e['blocked'] else 'no bloqueado'}, puntuación {e['score']:.4f}".replace(".", "{,}")
    if kind == "tool_call":
        args = ", ".join(f"{k}={v}" for k, v in e["args"].items())
        verdict = "permitida" if e["allowed"] else f"denegada por \\texttt{{{tex(e['control'])}}}"
        return rf"\texttt{{{tex(e['tool'])}}}({tex(args, 160)}) $\rightarrow$ {verdict}"
    if kind == "final_output":
        found = f" (DLP: {tex(', '.join(e['findings']))})" if e.get("findings") else ""
        return tex(e["text"], 200) + found
    return tex(json.dumps({k: v for k, v in e.items() if k not in ("ts", "run_id", "event")}, ensure_ascii=False))


def evidence_latex(telemetry: Path, out: Path, run_ids: list[str] = EVIDENCE_RUNS) -> int:
    lines, found = [], 0
    for rid in run_ids:
        events = last_run_events(telemetry, rid)
        if not events:
            continue
        found += 1
        cfg, variant = rid.split(":", 1)
        head = rf"\paragraph{{\texttt{{{tex(rid)}}}.}} Configuración {cfg}, variante \texttt{{{tex(variant)}}}."
        # Cada ejecución en una minipage: su título y su tabla no se separan entre páginas.
        lines += ["", r"\noindent\begin{minipage}{\textwidth}", head, "", r"\begin{footnotesize}"]
        rows = [rf"\texttt{{{tex(e['event'])}}} & {_describe(e)} \\" for e in events]
        lines += _tabular(r"Evento & Detalle \\", rows)
        lines += [r"\end{footnotesize}", r"\end{minipage}", r"\medskip"]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return found
