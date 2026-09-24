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


def test_variant_counts_match_plan(lab):
    from tfm_lab.attacks.scenarios import SCENARIOS
    counts = {s.id: len(campaign.variants(s, lab)) for s in SCENARIOS}
    assert counts == {"S1": 20, "S2": 20, "S3": 16, "S4": 15}


def test_benign_tasks_avoid_poisoned_contracts(lab):
    from tfm_lab.eval.benign import benign_tasks
    poisoned, clean = campaign.split_corpus(lab)
    tasks = benign_tasks(50, clean)
    assert len(tasks) == 50
    assert not any(p in t for p in poisoned for t in tasks)


def test_report_outputs(lab, monkeypatch, tmp_path):
    monkeypatch.setattr(campaign, "load_settings", lambda: lab)
    campaign.run_campaign(configs=["C0"], scenarios=["S1"], benign=False, dry_run=True)
    df = report.load_runs(lab.path("results"))
    report.plot_asr(df, tmp_path / "asr.png")
    report.latex_table(df, tmp_path / "asr.tex")
    assert (tmp_path / "asr.png").stat().st_size > 0
    assert "tabular" in (tmp_path / "asr.tex").read_text()
    lo, hi = report.wilson(5, 20)
    assert 0.1 < lo < 0.25 < hi < 0.5
