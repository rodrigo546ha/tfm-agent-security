"""Corpus de S2: 20 cargas distintas (5 semillas × 4 mutadores), una por contrato, y vigencias coherentes."""

import re
from collections import Counter

from tfm_lab.attacks import mutators
from tfm_lab.attacks.scenarios import INDIRECT_MUTATORS, INDIRECT_SEEDS, scenario_by_id
from tfm_lab.eval import campaign


def test_cada_par_semilla_mutador_aparece_una_vez(lab):
    manifest = campaign.poison_manifest(lab)
    pairs = Counter((m["seed"], m["mutator"]) for m in manifest.values())
    assert len(manifest) == 20
    assert set(pairs) == {(s, m) for s in range(len(INDIRECT_SEEDS)) for m in INDIRECT_MUTATORS}
    assert max(pairs.values()) == 1


def test_contratos_llevan_su_carga_y_los_limpios_ninguna(lab):
    manifest = campaign.poison_manifest(lab)
    poisoned, clean = campaign.split_corpus(lab)
    assert sorted(poisoned) == sorted(manifest) and len(clean) == 60
    contracts = lab.path("contracts")
    for cid, m in manifest.items():
        text = (contracts / f"{cid}.md").read_text(encoding="utf-8")
        assert mutators.apply(m["mutator"], INDIRECT_SEEDS[m["seed"]]) in text
    for cid in clean:
        text = (contracts / f"{cid}.md").read_text(encoding="utf-8")
        assert "externo.example" not in text and "<!--" not in text and "base64" not in text


def test_variantes_s2_salen_del_manifiesto(lab):
    vs = campaign.variants(scenario_by_id("S2"), lab)
    assert len(vs) == 20
    assert Counter(v["mutator"] for v in vs) == {m: 5 for m in INDIRECT_MUTATORS}
    assert all(re.fullmatch(r"S2-CT-\d{3}-s\d-\w+", v["id"]) for v in vs)


def test_vigencia_empieza_antes_de_acabar(lab):
    for p in lab.path("contracts").glob("CT-*.md"):
        inicio, fin = re.search(r"\*\*Vigencia:\*\* (\S+) a (\S+)\.", p.read_text(encoding="utf-8")).groups()
        assert inicio <= fin, p.stem
