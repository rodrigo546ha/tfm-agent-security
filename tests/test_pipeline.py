"""Test end-to-end del pipeline de campaña en modo dry-run (backend scripted, sin modelo)."""


from tfm_lab.eval import campaign, report


def test_campaign_dry_run(lab, monkeypatch):
    # Redirige el settings global del módulo al corpus del fixture.
    monkeypatch.setattr(campaign, "load_settings", lambda: lab)
    monkeypatch.setattr(report, "load_settings", lambda: lab)
    runs = campaign.run_campaign(configs=["C0", "C2"], scenarios=["S1", "S4"], benign=True, dry_run=True)
    assert runs.exists()
    df = report.load_runs(lab.path("results"))
    assert not df.empty
    asr = report.asr_table(df)
    assert "C0" in asr.columns and "C2" in asr.columns


def test_controls_fired_atribuye_cada_bloqueo():
    from tfm_lab.agent import AgentResult, ToolCallRecord
    pinned = {"convertir_divisa": "descripción no coincide con el manifiesto (pinning)"}
    r = AgentResult(final="", rejected_tools=pinned,
                    tool_calls=[ToolCallRecord("consultar_secretos", {}, False, "least_privilege"),
                                ToolCallRecord("leer_contrato", {}, True, sanitized=True),
                                ToolCallRecord("enviar_email", {}, False, "egress_allowlist")],
                    output_findings=["canary"])
    assert campaign.controls_fired(r) == ["egress_allowlist", "least_privilege", "output_dlp", "pinning",
                                          "tool_result_guard"]
    assert campaign.controls_fired(AgentResult(final="", blocked_input=True)) == ["input_guard"]
    assert campaign.controls_fired(AgentResult(final="ok")) == []


def test_variant_counts_match_plan(lab):
    from tfm_lab.attacks.scenarios import SCENARIOS
    counts = {s.id: len(campaign.variants(s, lab)) for s in SCENARIOS}
    assert counts == {"S1": 20, "S2": 20, "S3": 16, "S4": 15}


def test_benign_tasks_avoid_poisoned_contracts(lab):
    from tfm_lab.eval.benign import benign_tasks
    poisoned, clean = campaign.split_corpus(lab)
    tasks = benign_tasks(50, clean)
    assert len(tasks) == 50
    assert not any(p in t.text for p in poisoned for t in tasks)


def test_report_outputs(lab, monkeypatch, tmp_path):
    monkeypatch.setattr(campaign, "load_settings", lambda: lab)
    campaign.run_campaign(configs=["C0"], scenarios=["S1"], benign=False, dry_run=True)
    df = report.load_runs(lab.path("results"))
    report.plot_asr(df, tmp_path / "asr.png")
    report.latex_table(df, tmp_path / "asr.tex")
    assert (tmp_path / "asr.png").stat().st_size > 0
    assert "tabular" in (tmp_path / "asr.tex").read_text()
    report.breakdown_latex(df, tmp_path / "desglose.tex")
    desglose = (tmp_path / "desglose.tex").read_text()
    assert "Mutador" in desglose and "Semilla" in desglose
    b = report.breakdown(df)
    assert b.groupby("col")["n"].sum().loc["none"] == 4  # S1: 4 semillas con el mutador "none"
    assert "controls" in df.columns
    report.latency_latex(report.latency_table(df), tmp_path / "latencia.tex")
    assert "{,}" in (tmp_path / "latencia.tex").read_text()  # coma decimal


def test_atribucion_por_control(tmp_path):
    import pandas as pd
    df = pd.DataFrame([
        {"kind": "attack", "config": "C0", "variant": "S1-s0-none", "attack_success": True, "controls": []},
        {"kind": "attack", "config": "C0", "variant": "S1-s1-none", "attack_success": False, "controls": []},
        {"kind": "attack", "config": "C2", "variant": "S1-s0-none", "attack_success": False,
         "controls": ["input_guard", "output_dlp"]},
        {"kind": "attack", "config": "C2", "variant": "S1-s1-none", "attack_success": False,
         "controls": ["least_privilege"]},  # no tuvo éxito en C0: no cuenta
    ])
    att = report.attribution(df)
    assert att.attrs["n"] == 1
    assert att.loc["K1 Guardrail sobre el mensaje", "C2"] == 1
    assert att.loc["K4 Mínimo privilegio", "C2"] == 0
    assert att.loc["Siguen con éxito", "C2"] == 0
    report.attribution_latex(att, tmp_path / "atribucion.tex")
    assert "K10 DLP de salida & 1" in (tmp_path / "atribucion.tex").read_text()
    lo, hi = report.wilson(5, 20)
    assert 0.1 < lo < 0.25 < hi < 0.5
