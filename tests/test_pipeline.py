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
