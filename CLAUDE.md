# TFM — laboratorio de seguridad para agentes LLM

Trabajo Fin de Máster: *Arquitectura de seguridad de referencia para agentes LLM con acceso a herramientas:
modelado de amenazas con MITRE ATLAS y validación experimental en laboratorio*. Este repo es a la vez el
laboratorio (código) y la memoria (LaTeX en `memoria/`). Idioma de código, comentarios, commits y memoria: español.

## Restricciones que no se negocian
- **Coste cero**: nada de APIs ni servicios de pago. Solo Ollama local + modelos open source.
- **Horas acotadas**: cada sesión cierra un entregable concreto y añade una línea con las horas a `CHANGELOG.md`.
- **Repo público**: nunca datos reales, de clientes ni de empresa; todo el corpus es sintético.
  Secretos (HF_TOKEN) solo en `.env` (gitignored). Nunca escribas tokens en otro fichero.
- No cambiar título ni índice de la memoria: si falta tiempo, se recorta alcance (3 escenarios / 3 controles).

## Comandos
- `make test` — 45 tests sin modelo (backend heurístico). Ejecútalo tras cualquier cambio en `src/`.
- `make lint` — ruff y `sigma check` de las reglas de `deteccion/`.
- `make check` — comprueba Ollama, modelo y guardrail. Obligatorio antes de una campaña.
- `make campaign-fast` — S1+S4 en C0/C2 + 50 benignas (~20-30 min).
- `make reproduce` — campaña completa C0/C1/C2 × S1-S4 (~3-4 h). Lánzala con `caffeinate -i`.
- `make replica` — la misma campaña con `REPLICA_MODEL` (llama3.1:8b) en `results/replica/` (~50 min).
- `make promptfoo` — S1 con promptfoo 0.125.1 como segunda fuente de medida (~6 min, sin telemetría).
- `make report` — ASR con IC Wilson, falso bloqueo, latencia → `results/asr.{csv,png}` y `memoria/tablas/asr.tex`.
- `make memoria-figs && make memoria` — copia figuras y compila `memoria/memoria.pdf`.
- `uv run python -m tfm_lab.cli chat --config C2 "mensaje"` — probar el agente a mano.
- Python siempre vía `uv run` (macOS no tiene `python`). Ollama debe estar abierto (app o `ollama serve`).

## Arquitectura
- `src/tfm_lab/agent.py`: bucle de tool-calling propio con puntos de control explícitos.
- `controls/`: guardrail de entrada (Prompt Guard 2 o deberta ProtectAI), filtro de salida DLP, motor de políticas
  (mínimo privilegio, allowlist de egress, broker de credenciales `cred://`, HITL, pinning de herramientas).
- Configuraciones: C0 sin controles · C1 solo guardrail · C2 arquitectura completa. El broker es parte de C2.
- `attacks/scenarios.py`: S1 directa (20) · S2 indirecta vía contratos del corpus (20) · S3 descripción de
  herramienta envenenada (16) · S4 robo de credenciales + exfil (15). Mapeo ATLAS/OWASP ASI en cada escenario.
- `eval/detector.py`: éxito determinista por canario, herramienta prohibida o egress no confiable. Sin juez LLM.
- **Un error del modelo nunca cuenta como ataque fallido**: se marca `attack_success=null`, se excluye del informe
  y la campaña aborta tras 3 errores seguidos. Mantén esta garantía en cualquier cambio.
- Modelo: qwen3:8b (Mac de 16 GB), temperature 0, seed 42, num_ctx 8192, thinking off; fijar `model.digest`.

## Memoria (LaTeX)
- `memoria/memoria.tex`: 10 capítulos, máximo 20 caras de cuerpo (cada sección indica sus caras en comentario).
- Bibliografía en `memoria/referencias.bib` (BibTeX, `unsrt`). Toda cifra o afirmación externa lleva `\cite`.
- Resultados: nunca escribas números a mano; salen de `make report` (`tablas/asr.tex`, `figuras/asr.png`).
- Al recopilar fuentes, añade la entrada `.bib` con URL y fecha de consulta, y anota en el capítulo qué aporta.

## Forma de trabajar
- Al empezar: lee `docs/CONTEXTO.md`. Al terminar: actualiza su sección 5 (estado) y 6 (próximos pasos).
- Antes de cambiar el diseño experimental (escenarios, métricas, controles), explica el impacto y pide confirmación.
- Tras cambios en código: `make test && make lint`. Commits pequeños, en español.
- Los ADR van en `docs/adr/`; el modelo de amenazas en `docs/threat-model/`.

@docs/CONTEXTO.md
@CLAUDE.local.md
