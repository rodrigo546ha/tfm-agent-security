"""Guardrail de entrada: clasificador de prompt injection / jailbreak.

- HFClassifier: Llama Prompt Guard 2 86M (o deberta-v3 de ProtectAI) con transformers en CPU. Es el control
  que se mide en la memoria.
- HeuristicClassifier: patrones simples. SOLO para tests y para desarrollar sin el modelo descargado.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache


@dataclass
class GuardVerdict:
    blocked: bool
    score: float
    source: str
    reason: str = ""


POSITIVE_LABELS = {"LABEL_1", "MALICIOUS", "INJECTION", "JAILBREAK", "UNSAFE"}


class HFClassifier:
    def __init__(self, model_id: str, threshold: float = 0.5, max_chars: int = 1500):
        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("Instala el extra de guardrail: `uv sync --extra guard`") from exc
        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_id).eval()
        labels = {i: str(lbl).upper() for i, lbl in self.model.config.id2label.items()}
        pos = [i for i, lbl in labels.items() if lbl in POSITIVE_LABELS]
        self.pos_idx = pos or [max(labels)]
        self.threshold = threshold
        self.max_chars = max_chars
        self.name = model_id

    def _chunks(self, text: str) -> list[str]:
        # Prompt Guard 2 tiene ventana de 512 tokens: se trocea con solape y se toma la puntuación máxima.
        step = self.max_chars - 200
        return [text[i:i + self.max_chars] for i in range(0, max(len(text), 1), step)] or [""]

    def score(self, text: str) -> float:
        best = 0.0
        with self.torch.no_grad():
            for chunk in self._chunks(text):
                enc = self.tokenizer(chunk, return_tensors="pt", truncation=True, max_length=512)
                probs = self.torch.softmax(self.model(**enc).logits, dim=-1)[0]
                best = max(best, float(sum(probs[i] for i in self.pos_idx)))
        return best


_PATTERNS = [
    r"ignora (todas )?(las )?instrucciones", r"ignore (all )?(previous|prior) instructions",
    r"prompt de sistema", r"system prompt", r"modo (desarrollador|dan)", r"\bjailbreak\b",
    r"instrucci[oó]n (oculta|para el asistente|del sistema)", r"antes de (responder|usar esta herramienta)",
    r"env[ií]a(lo|la|los)? (a|al) .*http", r"consultar_secretos", r"obtener_credencial",
    r"base64", r"\[(mensaje|aviso) (del )?(administrador|sistema)", r"<!--",
]
_PAT_RE = re.compile("|".join(_PATTERNS), re.IGNORECASE)


class HeuristicClassifier:
    name = "heuristic"

    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold

    def score(self, text: str) -> float:
        hits = len(_PAT_RE.findall(text or ""))
        return min(1.0, 0.6 * hits)


@lru_cache(maxsize=4)
def get_classifier(backend: str, model_id: str, threshold: float):
    if backend == "hf":
        return HFClassifier(model_id, threshold)
    return HeuristicClassifier(threshold)


class InputGuard:
    def __init__(self, classifier) -> None:
        self.clf = classifier

    def check(self, text: str, source: str) -> GuardVerdict:
        s = self.clf.score(text)
        blocked = s >= self.clf.threshold
        return GuardVerdict(blocked, round(s, 4), source, f"{self.clf.name} score={s:.3f}" if blocked else "")
