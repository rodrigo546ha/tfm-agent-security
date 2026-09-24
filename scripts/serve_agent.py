"""API HTTP mínima que expone el agente para promptfoo. POST /chat {"message": "..."} -> {"final", ...}.

La configuración (C0/C1/C2) se elige con la variable de entorno TFM_CONFIG (por defecto C0).
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from pydantic import BaseModel

from tfm_lab.agent import Agent
from tfm_lab.controls import ControlSet
from tfm_lab.lab import build_context
from tfm_lab.llm import build_backend
from tfm_lab.settings import load_run_config, load_settings
from tfm_lab.tools.builtin import build_registry

app = FastAPI(title="TFM agent")
_S = load_settings()
_CFG = load_run_config(os.getenv("TFM_CONFIG", "C0"))


class ChatIn(BaseModel):
    message: str


@app.post("/chat")
def chat(inp: ChatIn) -> dict:
    ctx = build_context(_S, broker=_CFG.on("policy"))
    controls = ControlSet(_CFG, _S, known_secrets=[])
    reg = controls.register_tools(build_registry())
    agent = Agent(build_backend(_S.model), reg, controls, ctx, max_steps=_S.agent["max_steps"])
    r = agent.run(inp.message)
    return r.to_dict()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8100)
