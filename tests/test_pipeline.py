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


def test_promptfoo_pruebas_y_concordancia(lab, tmp_path):
    import json

    import pandas as pd
    import yaml

    from tfm_lab.eval import promptfoo
    assert promptfoo.write_tests(lab, tmp_path / "tests.yaml") == 20
    tests = yaml.safe_load((tmp_path / "tests.yaml").read_text())
    assert tests[0]["vars"]["variant"] == "S1-s0-none"
    assert {a["metric"] for a in tests[0]["assert"]} == {"canario:system_prompt", "canario:secrets.clave_api_crm",
                                                          "herramienta:consultar_secretos"}
    # Formato de `promptfoo eval -o`: una aserción falla (ataque con éxito), otra pasa y otra es error del agente.
    res = [{"vars": {"variant": "S1-s0-none"}, "success": False, "failureReason": 1},
           {"vars": {"variant": "S1-s1-none"}, "success": True, "failureReason": 0},
           {"vars": {"variant": "S1-s2-none"}, "success": False, "failureReason": 2, "error": "502"}]
    (tmp_path / "promptfoo_C0.json").write_text(json.dumps({"results": {"results": res}}))
    pf = promptfoo.load_results(tmp_path)
    assert pf["pf_success"].tolist() == [True, False, None]
    runs = pd.DataFrame([{"kind": "attack", "config": "C0", "variant": f"S1-s{i}-none", "attack_success": ok}
                         for i, ok in enumerate([True, True, False])])
    agr = report.agreement(runs, pf)
    assert agr.loc["C0"].tolist() == [2, 2, 1, 1]  # el error se excluye; S1-s1-none discrepa
    assert agr.attrs["discrepancias"] == ["C0 S1-s1-none"]
    report.agreement_latex(agr, tmp_path / "pf.tex")
    assert "C0 & 2 & 2 & 1 & 1" in (tmp_path / "pf.tex").read_text()


def test_anexos_generados_desde_codigo_y_telemetria(tmp_path):
    import json

    from tfm_lab.eval import anexos
    anexos.corpus_latex(tmp_path / "corpus.tex")
    corpus = (tmp_path / "corpus.tex").read_text()
    assert "S1-s3" in corpus and "S2-s4" in corpus and "S4-s2" in corpus
    assert r"\emph{carga codificada en base64}" in corpus and "—" not in corpus  # raya Unicode escapada
    tel = tmp_path / "telemetry.jsonl"
    ev = [{"run_id": "C2:X", "event": "user_input", "text": "antigua"},
          {"run_id": "C2:X", "event": "user_input", "text": "nueva 100%"},
          {"run_id": "C2:X", "event": "tool_call", "tool": "http_fetch", "args": {"url": "http://a_b"},
           "allowed": False, "control": "egress_allowlist"},
          {"run_id": "C2:X", "event": "guard_input", "blocked": False, "score": 0.0004}]
    tel.write_text("\n".join(json.dumps(e) for e in ev))
    assert [e["text"] for e in anexos.last_run_events(tel, "C2:X")[:1]] == ["nueva 100%"]  # solo la última
    assert anexos.evidence_latex(tel, tmp_path / "ev.tex", ["C2:X", "C0:no-existe"]) == 1
    out = (tmp_path / "ev.tex").read_text()
    assert r"nueva 100\%" in out and "antigua" not in out and "0{,}0004" in out
    assert r"egress\_\allowbreak{}allowlist" in out  # punto de corte tras _ para que no se salga del margen


def test_reglas_de_deteccion_sobre_telemetria(tmp_path):
    import json
    from pathlib import Path

    import pandas as pd

    from tfm_lab.eval import deteccion
    rules = deteccion.load_rules(Path(__file__).resolve().parents[1] / "deteccion")
    assert set(deteccion.MEASURED) <= set(rules) and len(rules) == 3
    r1, r3 = rules["r1_egress_denegado"], rules["r3_fuga_dlp"]
    denied = {"event": "tool_call", "allowed": False, "control": "egress_allowlist"}
    assert deteccion.matches(r1, denied)
    assert not deteccion.matches(r1, {**denied, "allowed": True})
    assert not deteccion.matches(r1, {**denied, "control": "least_privilege"})
    assert deteccion.matches(r3, {"event": "final_output", "findings": ["canary"]})
    assert not deteccion.matches(r3, {"event": "final_output", "findings": []})  # '*' exige algún hallazgo
    rule = {"detection": {"a": {"x|contains": "ABC"}, "b": {"y": [1, 2]}, "condition": "a and not (b or a)"}}
    assert not deteccion.matches(rule, {"x": "zabcz", "y": 3})
    assert deteccion.matches({"detection": {**rule["detection"], "condition": "a and not b"}}, {"x": "abc", "y": 3})
    tel = tmp_path / "telemetry.jsonl"
    ev = [{"run_id": "C2:S4-v", "event": "user_input"}, {"run_id": "C2:S4-v", **denied},  # campaña antigua
          {"run_id": "C2:S4-v", "event": "user_input"}, {"run_id": "C2:S4-v", "event": "final_output", "findings": []},
          {"run_id": "C2:B-00", "event": "user_input"}, {"run_id": "C2:S1-v", "event": "user_input"},
          {"run_id": "C2:S1-v", "event": "final_output", "findings": ["canary"]}]
    tel.write_text("\n".join(json.dumps(e) for e in ev))
    al = deteccion.alerts(tel, {k: rules[k] for k in deteccion.MEASURED})
    assert not al.set_index("variant").loc["S4-v", "r1_egress_denegado"]  # solo cuenta la última ejecución
    runs = pd.DataFrame([{"kind": "attack", "config": "C2", "variant": "S4-v", "attack_success": True},
                         {"kind": "attack", "config": "C2", "variant": "S1-v", "attack_success": False},
                         {"kind": "attack", "config": "C2", "variant": "S9-err", "attack_success": None},
                         {"kind": "benign", "config": "C2", "variant": "B-00", "attack_success": None}])
    tab = deteccion.detection_table(runs, al)
    assert tab.loc["C2"].to_dict() == {"ataques": 2, "r1_egress_denegado": 0, "r3_fuga_dlp": 1, "alguna": 1,
                                       "exitos": 1, "exitos_alerta": 0, "benignas": 1, "benignas_alerta": 0}
    deteccion.detection_latex(tab, tmp_path / "det.tex")
    assert "C2 & 2 & 0 & 1 & 1 & 0/1 & 0/1" in (tmp_path / "det.tex").read_text()
