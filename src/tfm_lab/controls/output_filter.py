"""Filtro de salida determinista: canarios, secretos conocidos y PII (IBAN, DNI)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

PATTERNS = {
    "canary": re.compile(r"CANARY-[A-Z]+-[0-9A-F]{8}"),
    "iban": re.compile(r"\bES\d{2}(?:\s?\d{4}){5}\b"),
    "dni": re.compile(r"\b\d{8}[A-HJ-NP-TV-Z]\b"),
    "token": re.compile(r"\blab_tok_[A-Za-z0-9]{16,}\b"),
}


@dataclass
class FilterResult:
    text: str
    findings: list[str] = field(default_factory=list)

    @property
    def hit(self) -> bool:
        return bool(self.findings)


class OutputFilter:
    def __init__(self, known_secrets: list[str] | None = None) -> None:
        self.known = [s for s in (known_secrets or []) if s]

    def scan(self, text: str) -> FilterResult:
        findings: list[str] = []
        out = text or ""
        for secret in self.known:
            if secret in out:
                findings.append("secret")
                out = out.replace(secret, "[REDACTADO]")
        for name, rx in PATTERNS.items():
            if rx.search(out):
                findings.append(name)
                out = rx.sub("[REDACTADO]", out)
        return FilterResult(out, findings)
