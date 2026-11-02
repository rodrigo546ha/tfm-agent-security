# promptfoo — escenario 1 contra el agente

`promptfoo` se usa como **segunda fuente de medida** del escenario 1 (inyección directa), independiente del
detector propio (`eval/detector.py`). Ataca al agente a través de un *provider* HTTP local; el agente nunca sale a
Internet.

- Las pruebas no se escriben a mano: `make promptfoo` las genera en `results/promptfoo/tests_s1.yaml` a partir de
  las 20 variantes de S1 de `attacks/scenarios.py`, con una aserción por criterio de éxito (canario del prompt de
  sistema, canario de la clave del CRM, `consultar_secretos` ejecutada con permiso).
- El agente se sirve con `scripts/serve_agent.py`, que lo construye con la misma función que la campaña
  (`campaign._agent`): mismos controles, broker y secretos conocidos por el DLP.
- Versión fijada (`promptfoo@0.125.1` vía `npx`), una petición cada vez (`-j 1`), sin caché, sin escribir en
  `~/.promptfoo` y sin telemetría ni comprobación de actualizaciones.

## Ejecución

```bash
make promptfoo        # C0, C1 y C2 (~6 min); CONFIGS="C0" bash scripts/promptfoo.sh para una sola
make report           # compara con runs.jsonl -> memoria/tablas/promptfoo.tex
```

Requiere Node (`npx`) y haber ejecutado antes la campaña (`make reproduce`) para tener `results/runs.jsonl`.
No requiere claves de API: el único proveedor es el agente local.
