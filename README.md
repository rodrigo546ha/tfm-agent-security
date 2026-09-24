# tfm-agent-security

Laboratorio del TFM **"Arquitectura de seguridad de referencia para agentes LLM con acceso a herramientas:
modelado de amenazas con MITRE ATLAS y validación experimental en laboratorio"**
(Máster en Ciberseguridad Defensiva y Ofensiva, UCM).

Todo el laboratorio es **local, open source y de coste cero**: modelo servido con Ollama, guardrail con
`transformers` en CPU, sin ninguna API de pago. Ningún dato es real; todo el corpus es sintético.

## Qué hace

Somete a un **agente LLM con herramientas** (CRM, contratos, web, email, credenciales) a cuatro escenarios de
ataque, bajo tres configuraciones de seguridad, y mide de forma **determinista** cuánto los mitiga la
arquitectura de referencia propuesta.

| | Escenario | ATLAS | OWASP ASI |
|---|---|---|---|
| S1 | Inyección directa de instrucciones | AML.T0051 | ASI01 |
| S2 | Inyección indirecta vía documento | AML.T0051 | ASI01/ASI06 |
| S3 | Envenenamiento de descripción de herramienta | AML.T0099 | ASI04 |
| S4 | Robo de credenciales + exfiltración | AML.T0098 | ASI03 |

Configuraciones: **C0** sin controles · **C1** solo guardrail de entrada · **C2** arquitectura completa
(guardrail entrada + filtro de salida + motor de políticas: mínimo privilegio, allowlist de egress, broker de
credenciales, confirmación humana, *pinning* de descripciones de herramientas).

Variantes: S1 20 · S2 20 (contratos con carga del corpus) · S3 16 · S4 15 = 71 ataques por configuración.

Métricas: **ASR** (attack success rate) por canario con IC de Wilson 95 %, **tasa de bloqueo de tareas legítimas** (50 tareas
benignas) y **latencia**.

## Requisitos

- macOS Apple Silicon (o Linux) · Python 3.11+ · [uv](https://docs.astral.sh/uv/) · [Ollama](https://ollama.com)
- Modelo: `qwen3:8b` (16 GB RAM) o `qwen3:4b` (8 GB). Plan B: `llama3.1:8b`.
- Guardrail de entrada: `meta-llama/Llama-Prompt-Guard-2-86M` (requiere aceptar la licencia en Hugging Face)
  o, sin licencia, `protectai/deberta-v3-base-prompt-injection-v2`.

## Arranque rápido

```bash
# 1. Modelo
ollama pull qwen3:8b            # anota el digest en config/lab.yaml

# 2. Entorno
make setup                      # uv venv + deps + requirements.txt

# 3. Datos y campaña
make reproduce                  # data -> manifest -> campaign (C0/C1/C2 × S1-S4) -> report

# Ver resultados
cat results/asr.csv ; open results/asr.png
```

Sin modelo instalado puedes validar todo el pipeline con datos scripted:

```bash
make test                       # 15 tests (backend heurístico, sin descargas)
python -m tfm_lab.cli campaign --dry-run
```

Guía paso a paso completa: **[docs/GUIA_ARRANQUE.md](docs/GUIA_ARRANQUE.md)**.

## Estructura

```
config/            lab.yaml, policy.yaml, configs/c0-c2.yaml, tool_manifest.json
src/tfm_lab/
  agent.py         bucle de tool-calling con puntos de control
  llm.py           backends Ollama / scripted
  lab.py           entorno simulado: gateway de egress (sumidero), vault de credenciales
  tools/           herramientas del agente + registro con manifiesto de integridad
  controls/        guardrail de entrada, filtro de salida, motor de políticas
  attacks/         escenarios, semillas y mutadores de variantes
  eval/            campaña, detector de ASR por canario, tareas benignas, informe
data/generated/    corpus sintético (regenerable)
attacks/           corpus de ataques versionado
promptfoo/         segunda fuente de medida (escenario 1)
docs/              modelo de amenazas, ADRs, evidencias, guía de despliegue
memoria/           fuente LaTeX de la memoria (tablas/asr.tex y figuras/ se generan con make report)
.github/workflows/ CI: ruff + tests en cada push
results/           runs.jsonl, summary.csv, asr.csv, asr.png (regenerable)
```

## Reproducibilidad

Parámetros deterministas (`temperature=0`, `seed=42`, `num_ctx=8192`, `think=off`), corpus con `seed=42`,
modelo fijado por digest, `uv.lock` + `requirements.txt`. Se verifica en una VM limpia en la semana del 26 ene (ver
`docs/deployment.md`). Detector de éxito por canario: sin juez LLM, veredicto reproducible.

## Licencia

MIT. Ver [LICENSE](LICENSE).
