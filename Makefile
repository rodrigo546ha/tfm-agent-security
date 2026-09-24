.PHONY: help setup data manifest campaign campaign-fast report chat test lint clean model-digest reproduce memoria memoria-figs

PY ?= python
export PYTHONPATH := src

help:  ## Muestra esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-16s\033[0m %s\n",$$1,$$2}'

setup:  ## Crea el entorno con uv e instala dependencias (incluye extra guard)
	uv venv
	uv sync --extra guard --extra dev
	uv export --no-hashes --no-dev --extra guard --format requirements-txt > requirements.txt

data:  ## Genera el corpus sintético (CRM, contratos, canarios)
	$(PY) -m tfm_lab.cli data

manifest:  ## Genera el manifiesto de integridad de herramientas
	$(PY) -m tfm_lab.cli manifest

campaign: data manifest  ## Ejecuta la campaña completa (C0/C1/C2 × S1-S4 + benignas) con Ollama
	$(PY) -m tfm_lab.cli campaign

campaign-fast: data manifest  ## Campaña rápida de humo (S1 y S4, C0 y C2)
	$(PY) -m tfm_lab.cli campaign --configs C0 C2 --scenarios S1 S4

report:  ## Genera tablas y gráfica de ASR desde results/
	$(PY) -m tfm_lab.cli report

chat:  ## Chat manual con el agente (make chat MSG="..." CFG=C2)
	$(PY) -m tfm_lab.cli chat --config $(or $(CFG),C2) "$(MSG)"

test:  ## Ejecuta la batería de tests (sin modelo, backend heurístico)
	TFM_GUARD_BACKEND=heuristic $(PY) -m pytest -q

lint:  ## ruff
	ruff check src tests

model-digest:  ## Muestra el digest del modelo instalado para fijarlo en config/lab.yaml
	@ollama show $${TFM_MODEL:-qwen3:8b} --modelfile 2>/dev/null | grep -i "^FROM" || \
		echo "Ejecuta primero: ollama pull $${TFM_MODEL:-qwen3:8b}"

reproduce: data manifest campaign report  ## Pipeline completo reproducible de principio a fin

clean:  ## Borra datos generados y resultados
	rm -rf data/generated/* results/* .pytest_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +

memoria-figs:  ## Copia las figuras de results/ a memoria/figuras/
	mkdir -p memoria/figuras && cp results/asr.png memoria/figuras/asr.png

memoria:  ## Compila la memoria LaTeX (memoria/memoria.pdf)
	cd memoria && latexmk -pdf -interaction=nonstopmode memoria.tex
