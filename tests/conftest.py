import os
import random
from pathlib import Path

import pytest

os.environ.setdefault("TFM_GUARD_BACKEND", "heuristic")  # los tests no descargan modelos

from tfm_lab.data import generate  # noqa: E402
from tfm_lab.settings import load_settings  # noqa: E402


@pytest.fixture(scope="session")
def lab(tmp_path_factory):
    """Genera un corpus sintético pequeño en un directorio temporal y ajusta las rutas del settings."""
    base = tmp_path_factory.mktemp("labdata")
    s = load_settings()
    s.raw["paths"] = {
        "db": str(base / "crm.sqlite"),
        "contracts": str(base / "contracts"),
        "canaries": str(base / "canaries.json"),
        "web": str(base / "web"),
        "results": str(base / "results"),
        "policy": s.raw["paths"]["policy"],
        "tool_manifest": str(base / "tool_manifest.json"),
    }
    rng = random.Random(1)
    from faker import Faker
    fk = Faker("es_ES")
    fk.seed_instance(1)
    canaries = generate.build_canaries(rng)
    generate.gen_db(s.path("db"), canaries, rng, fk)
    generate.gen_contracts(s.path("contracts"), rng, fk)
    generate.gen_web_fixtures(s.path("web"))
    Path(s.path("canaries")).write_text(__import__("json").dumps(canaries), encoding="utf-8")
    # manifiesto para el pinning
    from tfm_lab.tools import write_manifest
    from tfm_lab.tools.builtin import build_registry
    write_manifest(build_registry(), Path(s.path("tool_manifest")))
    return s
