# Registro de cambios y horas

Formato: cada entrada es una sesión de trabajo. `[Xh]` = horas de Rodrigo en esa sesión.
Sirve como bitácora de reproducibilidad y como control de las 45-60 h comprometidas.

## [No publicado]
### 2026-09-24 — Arranque del entorno [~Xh]
- Scaffold completo del laboratorio generado (agente, tools, controles, datos, ataques, evaluación).
- Revisión: 20/20/16/15 variantes (S1-S4), S2 sobre los 20 contratos con carga del corpus, detector con
  herramienta prohibida y egress no confiable, tareas benignas solo sobre contratos limpios, IC de Wilson,
  tabla LaTeX automática, DFD renderizado, uv.lock, CI en GitHub Actions. 15 tests en verde.
- 2026-09-25: preflight (`make check`), un error del modelo ya no cuenta como ataque fallido (se excluye y la
  campaña aborta tras 3 seguidos), mensaje claro si el guardrail está restringido, carga de `.env`. 18 tests.
- Pendiente: instalar Ollama, descargar qwen3:8b (16 GB RAM confirmados), fijar digest, acceso a Prompt Guard 2.

<!-- Plantilla de entrada:
### AAAA-MM-DD — <título> [Xh]
- <qué se hizo>
- <entregable cerrado de la sesión>
-->
