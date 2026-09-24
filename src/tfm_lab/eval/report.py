"""Análisis de resultados: ASR por configuración/escenario, tasa de falso bloqueo, latencia y gráficas."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from tfm_lab.settings import load_settings


def load_runs(results_dir: Path) -> pd.DataFrame:
    return pd.read_json(results_dir / "runs.jsonl", lines=True)


def asr_table(df: pd.DataFrame) -> pd.DataFrame:
    atk = df[df["scenario"] != "BENIGN"].copy()
    pivot = atk.pivot_table(index="scenario", columns="config", values="attack_success",
                            aggfunc="mean").round(3) * 100
    pivot.loc["GLOBAL"] = atk.groupby("config")["attack_success"].mean().round(3) * 100
    return pivot


def benign_table(df: pd.DataFrame) -> pd.DataFrame:
    b = df[df["scenario"] == "BENIGN"]
    return b[["config", "false_block_rate"]].set_index("config") * 100


def latency_table(df: pd.DataFrame) -> pd.DataFrame:
    atk = df[df["scenario"] != "BENIGN"]
    return atk.groupby("config")["latency_s"].agg(["mean", "median", "max"]).round(2)


def plot_asr(df: pd.DataFrame, out: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    table = asr_table(df).drop(index="GLOBAL", errors="ignore")
    ax = table.plot(kind="bar", figsize=(8, 4.5))
    ax.set_ylabel("ASR (%)")
    ax.set_xlabel("Escenario")
    ax.set_title("Tasa de éxito de ataque por escenario y configuración")
    ax.legend(title="Config")
    plt.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out, dpi=150)
    plt.close()


def main() -> None:
    results = load_settings().path("results")
    df = load_runs(results)
    asr = asr_table(df)
    print("\n=== ASR (%) por escenario × configuración ===")
    print(asr.to_string())
    print("\n=== Tasa de bloqueo de tareas legítimas (%) ===")
    print(benign_table(df).to_string())
    print("\n=== Latencia (s) ===")
    print(latency_table(df).to_string())

    asr.to_csv(results / "asr.csv")
    plot_asr(df, results / "asr.png")
    print(f"\nGráfica -> {results / 'asr.png'}")


if __name__ == "__main__":
    main()
