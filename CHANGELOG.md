# Registro de cambios y horas

Formato: cada entrada es una sesión de trabajo. `[Xh]` = horas de Rodrigo en esa sesión.
Sirve como bitácora de reproducibilidad y como control de las 45-60 h comprometidas.

Las horas desde el 31 oct son estimaciones a partir de la actividad registrada en la sesión de Claude Code
(intervalos sin más de 20 min de inactividad); las campañas desatendidas no cuentan. Las de septiembre se
estiman a partir de las horas de los commits. Acumulado estimado: ~5 h.

## [No publicado]
### 2026-11-01 — Campaña completa, corpus de S2 y capítulo 4 [~1h]
- Campaña completa (363 filas, 52 min). C2 para los 25 éxitos de C0, sin falsos bloqueos. Detectado que los 20
  contratos de S2 llevan la misma carga: S2 no es válido hasta corregir el generador.
- Generador de S2 corregido (5 semillas × 4 mutadores, manifiesto `cargas_s2.json`), vigencia ordenada y CRM
  reproducible (semilla del `random` global para `nif()`). 39 tests. Campaña completa repetida: ASR global
  C0/C1/C2 48,6/37,1/2,9 %; los 2 éxitos de C2 son secuestros en S2 contenidos por el broker y la allowlist.
  Decidido: se cuentan y se explican; S3 (25 %) se documenta como resultado.
- Capítulo 4 redactado (activos, DFD con puntos de entrada E1-E4, STRIDE, matriz T1-T7 priorizada, fuera de
  alcance). Mapeo comprobado en ATLAS 2026.10 y en el PDF de OWASP: S3 pasa a AML.T0110, S2 a
  AML.T0051.001 + T0099 sin ASI06, T7 sin ASI05. Corregido en `scenarios.py`, README y modelo de amenazas.
- Bibliografía: entradas en `@misc` con URL y fecha visibles en `unsrt`; ATLAS y OWASP con versión.
- `tectonic` instalado (Homebrew); `make memoria` lo usa si no hay `latexmk`. Rayas Unicode cambiadas por
  `---` (memoria y `report.py`), títulos de la bibliografía protegidos de minúsculas, URL del repo en el anexo A.
  La memoria compila (7 páginas); el capítulo 4 ocupa ~2,6 caras.
- Capítulo 3 redactado (PASTA y STRIDE, diseño experimental, métricas con IC de Wilson, regla de errores, ética y
  legalidad), ~1,6 caras. Cinco fuentes nuevas en `referencias.bib`. La memoria compila (10 páginas).

### 2026-10-31 — Tareas benignas con oráculo [~1h]
- Contraste del plan de arranque (23 sep) con el repo: huecos en utilidad, banda de ASR en C0 y reglas de detección.
- Oráculo determinista por plantilla benigna (`check_benign`): columna `benign_ok`/`benign_reason`, tabla de tareas
  completadas con IC de Wilson y aviso si C0 < 90 % (`results/benignas.csv`, `memoria/tablas/benignas.tex`).
- Digest de `qwen3:8b` fijado en `config/lab.yaml`. 34 tests en verde.
- `num_predict: 1024` y columna `truncated` tras un bucle de generación de 2 h en una variante base64. 35 tests.
- `campaign-fast` completa: C0 cae en S1 y S4 dentro de la banda 30-80 %, C2 lo para todo sin falsos bloqueos,
  C0 completa el 98 % de las benignas. El abort de Ollama en `S4-s1-base64` se queda como error excluido (n=14).

### 2026-09-24 — Arranque del entorno [~3h]
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
