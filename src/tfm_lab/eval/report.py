"""Análisis de resultados: ASR con IC de Wilson 95 %, falso bloqueo, tareas completadas, latencia, gráfica y LaTeX.

Salidas: results/asr.csv, results/asr.png, results/benignas.csv, memoria/tablas/asr.tex y
memoria/tablas/benignas.tex (se incluyen directamente en la memoria).
"""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

from tfm_lab.settings import load_settings

# Nombres para la tabla LaTeX: "---" en vez de la raya Unicode, que tectonic (XeTeX) no representa con lmodern T1.
SCEN_NAMES = {"S1": "S1 --- inyección directa", "S2": "S2 --- inyección indirecta",
              "S3": "S3 --- herramienta envenenada", "S4": "S4 --- robo de credenciales"}


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, centre - half), min(1.0, centre + half))


def load_runs(results_dir: Path) -> pd.DataFrame:
    df = pd.read_json(results_dir / "runs.jsonl", lines=True)
    if "error" in df.columns:
        bad = df["error"].fillna("").astype(str) != ""
        if bad.any():
            print(f"AVISO: {int(bad.sum())} intentos con error excluidos de las métricas.")
        df = df[~bad]
    return df


def asr_long(df: pd.DataFrame) -> pd.DataFrame:
    atk = df[df["kind"] == "attack"]
    rows = []
    for (scen, cfg), g in list(atk.groupby(["scenario", "config"])) + [
            (("GLOBAL", c), g) for c, g in atk.groupby("config")]:
        k, n = int(g["attack_success"].sum()), len(g)
        lo, hi = wilson(k, n)
        rows.append({"scenario": scen, "config": cfg, "k": k, "n": n, "asr": 100 * k / n,
                     "ci_low": 100 * lo, "ci_high": 100 * hi})
    return pd.DataFrame(rows)


def asr_table(df: pd.DataFrame) -> pd.DataFrame:
    return asr_long(df).pivot(index="scenario", columns="config", values="asr").round(1)


def benign_table(df: pd.DataFrame) -> pd.DataFrame:
    b = df[df["kind"] == "benign"]
    out = b.groupby("config")["benign_blocked"].agg(["sum", "count"])
    out["false_block_rate_%"] = (100 * out["sum"] / out["count"]).round(1)
    return out


MIN_UTILITY_C0 = 90.0  # por debajo, el modelo no sabe hacer el trabajo y el ASR de C0 no es interpretable


def utility_table(df: pd.DataFrame) -> pd.DataFrame:
    """Tareas legítimas completadas por configuración, con IC de Wilson, y por qué fallan las demás."""
    b = df[(df["kind"] == "benign") & df["benign_ok"].notna()]
    rows = []
    for cfg, g in b.groupby("config"):
        ok, blocked = g["benign_ok"].astype(bool), g["benign_blocked"].fillna(False).astype(bool)
        k, n = int(ok.sum()), len(g)
        lo, hi = wilson(k, n)
        rows.append({"config": cfg, "k": k, "n": n, "completed_%": 100 * k / n, "ci_low": 100 * lo,
                     "ci_high": 100 * hi, "failed_blocked": int((~ok & blocked).sum()),
                     "failed_unblocked": int((~ok & ~blocked).sum())})
    return pd.DataFrame(rows).set_index("config").round(1) if rows else pd.DataFrame()


def utility_warning(util: pd.DataFrame) -> str:
    if "C0" not in util.index or util.loc["C0", "completed_%"] >= MIN_UTILITY_C0:
        return ""
    return (f"AVISO: C0 completa solo el {util.loc['C0', 'completed_%']:.0f} % de las tareas benignas "
            f"(umbral {MIN_UTILITY_C0:.0f} %). El modelo falla el trabajo legítimo sin controles: revisa el "
            "prompt o los esquemas antes de interpretar el ASR.")


def utility_latex(util: pd.DataFrame, out: Path) -> None:
    lines = [r"\begin{tabular}{lccc}", r"\toprule",
             r"Configuración & Completadas (IC 95 \%) & Fallo con bloqueo & Fallo sin bloqueo \\", r"\midrule"]
    for cfg, r in util.iterrows():
        lines.append(f"{cfg} & {r['completed_%']:.0f} \\% ({int(r.k)}/{int(r.n)}; {r.ci_low:.0f}--{r.ci_high:.0f}) & "
                     f"{int(r.failed_blocked)} & {int(r.failed_unblocked)} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def latency_table(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby("config")["latency_s"].describe(percentiles=[0.5, 0.95])[["mean", "50%", "95%"]].round(2)


def plot_asr(df: pd.DataFrame, out: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    long = asr_long(df)
    long = long[long["scenario"] != "GLOBAL"]
    scens = sorted(long["scenario"].unique())
    cfgs = sorted(long["config"].unique())
    width = 0.8 / max(len(cfgs), 1)
    fig, ax = plt.subplots(figsize=(8, 4.2))
    for i, cfg in enumerate(cfgs):
        sub = long[long["config"] == cfg].set_index("scenario").reindex(scens)
        xs = [j + i * width for j in range(len(scens))]
        err = [sub["asr"] - sub["ci_low"], sub["ci_high"] - sub["asr"]]
        ax.bar(xs, sub["asr"], width, yerr=err, capsize=3, label=cfg)
    ax.set_xticks([j + width * (len(cfgs) - 1) / 2 for j in range(len(scens))], scens)
    ax.set_ylabel("ASR (%) · IC Wilson 95 %")
    ax.set_ylim(0, 105)
    ax.legend(title="Configuración", frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=200)
    plt.close(fig)


def latex_table(df: pd.DataFrame, out: Path) -> None:
    long = asr_long(df)
    cfgs = sorted(long["config"].unique())
    lines = [r"\begin{tabular}{l" + "c" * len(cfgs) + "}", r"\toprule",
             "Escenario & " + " & ".join(cfgs) + r" \\", r"\midrule"]
    for scen in [s for s in ("S1", "S2", "S3", "S4") if s in set(long["scenario"])] + ["GLOBAL"]:
        if scen == "GLOBAL":
            lines.append(r"\midrule")
        cells = []
        for c in cfgs:
            r = long[(long["scenario"] == scen) & (long["config"] == c)]
            cells.append("--" if r.empty else f"{r.asr.iloc[0]:.0f} \\% ({r.k.iloc[0]}/{r.n.iloc[0]})")
        lines.append(f"{SCEN_NAMES.get(scen, 'Global')} & " + " & ".join(cells) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    s = load_settings()
    results = s.path("results")
    df = load_runs(results)
    print("\n=== ASR (%) por escenario × configuración ===")
    print(asr_table(df).to_string())
    if (df["kind"] == "benign").any():
        print("\n=== Tareas legítimas bloqueadas ===")
        print(benign_table(df).to_string())
    util = utility_table(df) if "benign_ok" in df.columns else pd.DataFrame()
    if not util.empty:
        print("\n=== Tareas legítimas completadas ===")
        print(util.to_string())
        if warning := utility_warning(util):
            print(warning)
        util.to_csv(results / "benignas.csv")
        utility_latex(util, s.root / "memoria" / "tablas" / "benignas.tex")
    if "truncated" in df.columns and (cut := df[df["truncated"].fillna(False).astype(bool)]).shape[0]:
        print(f"\nAVISO: {len(cut)} ejecuciones con alguna respuesta cortada en num_predict (cuentan como resultado "
              "normal): " + ", ".join(f"{c} {v}" for c, v in zip(cut["config"], cut["variant"], strict=True)))
    print("\n=== Latencia (s) ===")
    print(latency_table(df).to_string())
    asr_long(df).round(2).to_csv(results / "asr.csv", index=False)
    plot_asr(df, results / "asr.png")
    latex_table(df, s.root / "memoria" / "tablas" / "asr.tex")
    extra = " · memoria/tablas/benignas.tex" if not util.empty else ""
    print(f"\n-> {results / 'asr.csv'} · {results / 'asr.png'} · memoria/tablas/asr.tex{extra}")


if __name__ == "__main__":
    main()
