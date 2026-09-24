# ADR 0001 — Modelo local con Ollama y guardrail en CPU

- Estado: aceptado (2026-09-23)
- Contexto: el TFM exige coste cero y reproducibilidad; el equipo es un MacBook Air Apple Silicon.

## Decisión
Servir el modelo objetivo con **Ollama nativo** (Metal) y el guardrail de entrada con `transformers` en CPU.
Modelo objetivo: **Qwen3 8B Q4_K_M** (Plan B: Llama 3.1 8B; con 8 GB, Qwen3 4B). Parámetros deterministas
(temperature 0, seed 42, num_ctx 8192, thinking off). Modelo fijado por digest.

## Consecuencias
- (+) Coste cero, sin fuga de datos a terceros, reproducible.
- (+) En Mac, Ollama nativo usa GPU; los contenedores no -> Docker queda solo para reproducir en Linux/VM.
- (-) Modelos ~8B: menor capacidad que uno comercial; se asume y se documenta como limitación.
