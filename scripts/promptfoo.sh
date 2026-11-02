#!/usr/bin/env bash
# Ejecuta promptfoo (S1) contra el agente servido en local, una vez por configuración.
# Sin telemetría ni comprobación de actualizaciones: el único destino de las peticiones es 127.0.0.1.
set -euo pipefail

PROMPTFOO_VERSION=0.125.1
PORT=8100
export PROMPTFOO_DISABLE_TELEMETRY=1 PROMPTFOO_DISABLE_UPDATE=1 PROMPTFOO_DISABLE_SHARING=1
export REQUEST_TIMEOUT_MS=600000  # una variante base64 tarda ~1 min

uv run python -m tfm_lab.cli promptfoo-tests
for cfg in ${CONFIGS:-C0 C1 C2}; do
  TFM_CONFIG=$cfg uv run python scripts/serve_agent.py > "results/promptfoo/serve_$cfg.log" 2>&1 &
  pid=$!
  trap 'kill $pid 2>/dev/null || true' EXIT
  for _ in $(seq 1 120); do  # el guardrail tarda en cargar
    curl -s -o /dev/null "http://127.0.0.1:$PORT/docs" && break
    sleep 1
  done
  # Una petición cada vez (-j 1): en paralelo, Ollama podría agrupar peticiones y cambiar el resultado.
  npx --yes "promptfoo@$PROMPTFOO_VERSION" eval -c promptfoo/promptfooconfig.yaml \
    --no-cache --no-write --no-progress-bar -j 1 -o "results/promptfoo_$cfg.json" || true  # sale con 100 si falla alguna aserción
  kill $pid
  wait $pid 2>/dev/null || true
done
