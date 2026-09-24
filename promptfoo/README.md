# promptfoo — escenario 1 contra el agente

`promptfoo` se usa como **segunda fuente de medida** del escenario 1 (inyección directa), independiente del
harness propio. Ataca al agente a través de un *provider* HTTP local; el agente nunca sale a Internet.

## Puesta en marcha

1. Levanta el agente como API local (script auxiliar en `scripts/serve_agent.py`):
   ```bash
   make data manifest
   TFM_CONFIG=C0 python scripts/serve_agent.py   # expone POST http://127.0.0.1:8100/chat
   ```
2. En otra terminal:
   ```bash
   npx promptfoo@latest eval -c promptfoo/promptfooconfig.yaml
   npx promptfoo@latest view
   ```
3. Repite con `TFM_CONFIG=C1` y `TFM_CONFIG=C2` para comparar.

No requiere claves de API: el único proveedor es el agente local.
