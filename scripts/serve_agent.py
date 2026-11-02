"""API HTTP mínima que expone el agente para promptfoo. POST /chat {"message": "..."} -> {"final", ...}.

La configuración (C0/C1/C2) se elige con la variable de entorno TFM_CONFIG (por defecto C0). El agente se construye
con la misma función que la campaña (`campaign._agent`), de modo que los controles, el broker y los secretos
conocidos por el DLP son idénticos: promptfoo mide el mismo agente que `runs.jsonl`.
"""

from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from tfm_lab.eval.campaign import _agent
from tfm_lab.llm import build_backend
from tfm_lab.settings import load_settings
from tfm_lab.telemetry import Telemetry

app = FastAPI(title="TFM agent")
_S = load_settings()
_CFG = os.getenv("TFM_CONFIG", "C0")
_LLM = build_backend(_S.model)


class ChatIn(BaseModel):
    message: str


@app.post("/chat")
def chat(inp: ChatIn) -> dict:
    agent, _ = _agent(_LLM, _S, _CFG, Telemetry())  # agente y contexto nuevos en cada petición, como en la campaña
    r = agent.run(inp.message)
    if r.error:
        # Un error del modelo no es un ataque fallido: promptfoo lo registra como error, no como aserción superada.
        raise HTTPException(status_code=502, detail=r.error)
    return r.to_dict()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8100)
