"""Reglas de detección (Sigma) sobre la telemetría de la campaña: qué ejecuciones dejan una alerta.

Sigma no trae un traductor para JSONL, así que aquí se interpreta el subconjunto que usan las reglas de
`deteccion/`: selecciones campo-valor (una lista de valores es un OR), comodines `*`, el modificador `|contains`
y condiciones con `and`, `or`, `not` y paréntesis. Si un campo del evento es una lista, basta con que un
elemento coincida (así `findings: '*'` exige al menos un hallazgo). La sintaxis de las reglas se valida aparte
con `sigma check`.
"""

from __future__ import annotations

import json
import re
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

# R2 necesita correlación por usuario, que el laboratorio no puede medir (una petición por tarea y sin identidad):
# se escribe y se valida, pero no entra en la tabla.
MEASURED = ["r1_egress_denegado", "r3_fuga_dlp"]


def load_rules(rules_dir: Path) -> dict[str, dict]:
    return {f.stem: yaml.safe_load(f.read_text(encoding="utf-8")) for f in sorted(rules_dir.glob("*.yml"))}


def _value_matches(actual: Any, expected: Any, modifier: str | None) -> bool:
    if isinstance(actual, list):
        return any(_value_matches(a, expected, modifier) for a in actual)
    if isinstance(expected, list):
        return any(_value_matches(actual, e, modifier) for e in expected)
    if isinstance(expected, bool) or isinstance(actual, bool):
        return actual is expected
    if actual is None:
        return False
    a, e = str(actual).lower(), str(expected).lower()  # Sigma compara sin distinguir mayúsculas
    return e in a if modifier == "contains" else fnmatchcase(a, e)


def _selection_matches(event: dict, selection: dict) -> bool:
    for key, expected in selection.items():
        field, _, modifier = key.partition("|")
        if field not in event or not _value_matches(event[field], expected, modifier or None):
            return False
    return True


def _condition(cond: str, hits: dict[str, bool]) -> bool:
    """Evalúa `and`/`or`/`not`/paréntesis sobre los nombres de selección, sin `eval`."""
    tokens = re.findall(r"\(|\)|\w+", cond)
    pos = 0

    def expr() -> bool:
        nonlocal pos
        val = term()
        while pos < len(tokens) and tokens[pos] == "or":
            pos += 1
            val = term() or val
        return val

    def term() -> bool:
        nonlocal pos
        val = factor()
        while pos < len(tokens) and tokens[pos] == "and":
            pos += 1
            val = factor() and val
        return val

    def factor() -> bool:
        nonlocal pos
        tok = tokens[pos]
        pos += 1
        if tok == "not":
            return not factor()
        if tok == "(":
            val = expr()
            pos += 1  # ")"
            return val
        return hits[tok]

    return expr()


def matches(rule: dict, event: dict) -> bool:
    det = rule["detection"]
    hits = {name: _selection_matches(event, sel) for name, sel in det.items() if name != "condition"}
    return _condition(det["condition"], hits)


def last_runs(telemetry: Path) -> dict[str, list[dict]]:
    """Eventos de la última ejecución de cada run_id (telemetry.jsonl acumula todas las campañas)."""
    runs: dict[str, list[dict]] = {}
    for line in telemetry.read_text(encoding="utf-8").splitlines():
        e = json.loads(line)
        if e["event"] == "user_input":
            runs[e["run_id"]] = []
        runs.setdefault(e["run_id"], []).append(e)
    return runs


def alerts(telemetry: Path, rules: dict[str, dict]) -> pd.DataFrame:
    """Una fila por ejecución (config, variante) con una columna booleana por regla."""
    rows = []
    for rid, events in last_runs(telemetry).items():
        if ":" not in rid:
            continue
        cfg, variant = rid.split(":", 1)
        rows.append({"config": cfg, "variant": variant,
                     **{name: any(matches(rule, e) for e in events) for name, rule in rules.items()}})
    return pd.DataFrame(rows)


def detection_table(df: pd.DataFrame, al: pd.DataFrame, measured: list[str] = MEASURED) -> pd.DataFrame:
    """Por configuración: ataques con alerta de cada regla y de alguna, éxitos detectados y benignas con alerta.
    Las ejecuciones con error del modelo se excluyen, igual que en el ASR."""
    m = df.merge(al, on=["config", "variant"], how="left")
    m[measured] = m[measured].fillna(False).astype(bool)
    m["alguna"] = m[measured].any(axis=1)
    atk = m[(m["kind"] == "attack") & m["attack_success"].notna()]
    ben = m[m["kind"] == "benign"]
    ok = atk["attack_success"].astype(bool)
    out = pd.DataFrame({
        "ataques": atk.groupby("config").size(),
        **{r: atk.groupby("config")[r].sum() for r in measured},
        "alguna": atk.groupby("config")["alguna"].sum(),
        "exitos": ok.groupby(atk["config"]).sum(),
        "exitos_alerta": (ok & atk["alguna"]).groupby(atk["config"]).sum(),
        "benignas": ben.groupby("config").size(),
        "benignas_alerta": ben.groupby("config")["alguna"].sum(),
    }).fillna(0).astype(int)
    return out


def detection_latex(tab: pd.DataFrame, out: Path) -> None:
    lines = [r"\begin{tabular}{lcccccc}", r"\toprule",
             r"Config. & Ataques & Alerta R1 & Alerta R3 & Alguna & Éxitos con alerta & Benignas con alerta \\",
             r"\midrule"]
    lines += [f"{cfg} & {r.ataques} & {r.r1_egress_denegado} & {r.r3_fuga_dlp} & {r.alguna} & "
              f"{r.exitos_alerta}/{r.exitos} & {r.benignas_alerta}/{r.benignas} \\\\" for cfg, r in tab.iterrows()]
    lines += [r"\bottomrule", r"\end{tabular}"]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
