"""Un error del modelo nunca debe contarse como 'ataque fallido' (sesgaría el ASR a la baja)."""

import pytest

from tfm_lab.eval import campaign, report
from tfm_lab.llm import ScriptedBackend


class _Broken(ScriptedBackend):
    def chat(self, messages, tools):
        raise ConnectionError("Ollama no disponible")


def test_model_errors_abort_and_are_not_attack_failures(lab, monkeypatch):
    monkeypatch.setattr(campaign, "load_settings", lambda: lab)
    monkeypatch.setattr(campaign, "ScriptedBackend", lambda *_a, **_k: _Broken([]))
    with pytest.raises(RuntimeError, match="3 errores seguidos"):
        campaign.run_campaign(configs=["C0"], scenarios=["S1"], benign=False, dry_run=True)
    raw = (lab.path("results") / "runs.jsonl").read_text().splitlines()
    assert len(raw) == 3  # aborta al tercer error, no sigue acumulando filas falsas
    assert all('"attack_success": null' in r for r in raw)
    assert report.load_runs(lab.path("results")).empty  # excluidas de las métricas


def test_preflight_fails_without_ollama(lab):
    lab.raw["model"]["host"] = "http://127.0.0.1:1"  # puerto cerrado
    try:
        with pytest.raises(campaign.PreflightError, match="Ollama"):
            campaign.preflight(lab, ["C0"])
    finally:
        lab.raw["model"]["host"] = "http://127.0.0.1:11434"


def test_dotenv_does_not_override(tmp_path, monkeypatch):
    import os

    from tfm_lab.settings import load_dotenv
    env = tmp_path / ".env"
    env.write_text("# comentario\nTFM_X_NEW='abc'\nTFM_X_SET=desde_env\n")
    monkeypatch.setenv("TFM_X_SET", "desde_shell")
    monkeypatch.delenv("TFM_X_NEW", raising=False)
    load_dotenv(env)
    assert os.environ["TFM_X_NEW"] == "abc"
    assert os.environ["TFM_X_SET"] == "desde_shell"
