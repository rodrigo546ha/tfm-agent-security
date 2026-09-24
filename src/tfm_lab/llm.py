"""Backends de LLM. OllamaBackend para el laboratorio real; ScriptedBackend para tests sin modelo."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

# Respuesta normalizada: {"content": str, "tool_calls": [{"name": str, "arguments": dict}]}
LLMResponse = dict[str, Any]


class LLMBackend(Protocol):
    name: str

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> LLMResponse: ...


class OllamaBackend:
    """Cliente de Ollama nativo (Metal en Apple Silicon). Parámetros deterministas desde config/lab.yaml."""

    def __init__(self, model: str, host: str, options: dict[str, Any] | None = None, think: bool = False):
        from ollama import Client

        self.name = model
        self.client = Client(host=host)
        self.options = options or {}
        self.think = think

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": self.name,
            "messages": messages,
            "tools": tools or None,
            "options": self.options,
        }
        try:
            resp = self.client.chat(think=self.think, **kwargs)
        except TypeError:  # SDK antiguo sin parámetro think
            resp = self.client.chat(**kwargs)
        msg = resp.message
        calls = []
        for tc in msg.tool_calls or []:
            calls.append({"name": tc.function.name, "arguments": dict(tc.function.arguments or {})})
        return {"content": msg.content or "", "tool_calls": calls}


class ScriptedBackend:
    """Backend determinista para tests: una lista de respuestas o una función (messages, tools) -> respuesta."""

    def __init__(self, script: list[LLMResponse] | Callable[[list, list], LLMResponse], name: str = "scripted"):
        self.name = name
        self._script = script
        self._i = 0

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> LLMResponse:
        if callable(self._script):
            return self._script(messages, tools)
        resp = self._script[min(self._i, len(self._script) - 1)]
        self._i += 1
        return {"content": resp.get("content", ""), "tool_calls": resp.get("tool_calls", [])}


def build_backend(model_cfg: dict[str, Any]) -> OllamaBackend:
    return OllamaBackend(
        model=model_cfg["name"],
        host=model_cfg["host"],
        options=model_cfg.get("options"),
        think=model_cfg.get("think", False),
    )
