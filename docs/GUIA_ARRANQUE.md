# Guía de arranque — paso a paso

Esta guía te lleva de cero a la primera campaña completa. Está pensada para tu MacBook Air (Apple Silicon) y
respeta las dos restricciones del TFM: **coste cero** y **dentro de las horas estimadas**.

---

## 1. Recursos que debes conseguir o conectar

Todo es gratuito y open source. Nada de esto tiene coste ni requiere tarjeta.

### Software local (instalar una vez)
| Recurso | Para qué | Cómo |
|---|---|---|
| **Ollama** | Servir el modelo LLM (usa la GPU del Mac vía Metal) | `brew install ollama` o [ollama.com/download](https://ollama.com/download) |
| **Modelo Qwen3 8B** | El "cerebro" del agente objetivo | `ollama pull qwen3:8b` (con 8 GB de RAM: `qwen3:4b`) |
| **uv** | Gestor de entorno/paquetes Python (ya lo tienes) | [docs.astral.sh/uv](https://docs.astral.sh/uv/) |
| **Python 3.11+** | Runtime | viene con uv o con tu nvm/Homebrew |
| **gh** (GitHub CLI) | Crear el repo público | `brew install gh` |
| **Node 22** (ya lo tienes) | Solo para `promptfoo` (segunda fuente de medida) | nvm |

Ya instalados según tus notas: OrbStack, VirtualBox, nvm. **OrbStack/Docker no hacen falta en el Mac**
(Ollama en contenedor no usa GPU); Docker es solo para reproducir en la VM al final.

### Cuentas / accesos a conectar
| Recurso | Para qué | Acción |
|---|---|---|
| **Cuenta de Hugging Face** (gratis) | Descargar el guardrail de entrada | Regístrate y `huggingface-cli login` |
| **Licencia de Llama Prompt Guard 2** | Modelo de guardrail (licencia Llama 4 Community) | Acepta la licencia en [su página de HF](https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-86M) |
| **Cuenta de GitHub** (ya la tienes) | Repo público accesible a los tutores | — |

> **Alternativa sin licencia:** si no quieres pedir acceso a Meta, usa
> `protectai/deberta-v3-base-prompt-injection-v2` (sin gate). Se activa con
> `export TFM_GUARD_MODEL=protectai/deberta-v3-base-prompt-injection-v2`.

### Nada de esto se necesita
Sin APIs de pago (OpenAI/Anthropic/etc.), sin servicios cloud, sin datasets con licencia. El corpus es
sintético y se genera en tu máquina.

---

## 2. Antes de nada: confirma RAM y modelo (5 min)

```bash
sysctl -n hw.memsize        # bytes de RAM: /1073741824 = GB
```
- **16 GB o más** → `qwen3:8b` (recomendado).
- **8 GB** → `qwen3:4b` (cambia `model.name` en `config/lab.yaml`).

```bash
ollama pull qwen3:8b
ollama show qwen3:8b --modelfile | grep -i "^FROM"   # copia el digest a config/lab.yaml (model.digest)
```

---

## 3. Montar el proyecto (10 min)

```bash
# 1. Crea el repo (público, MIT ya incluido)
cd ~/ruta/donde/lo/quieras
gh repo create tfm-agent-security --public --clone   # o clona el que ya tengas y copia el scaffold dentro

# 2. Copia dentro el contenido del scaffold que te he entregado

# 3. Entorno + dependencias
make setup            # crea .venv, instala todo, exporta requirements.txt

# 4. Guardrail real (una vez)
huggingface-cli login # pega tu token de HF
```

Verifica que todo enciende **sin modelo** (no descarga nada):
```bash
make test
```

> En zsh no pegues los comentarios `# ...` detrás de los comandos: make los interpreta como objetivos.

```bash
python -m tfm_lab.cli campaign --dry-run   # valida el pipeline entero
```

---

## 4. Primera campaña real (30–60 min de máquina)

```bash
# Genera el corpus sintético y el manifiesto de integridad
make data
make manifest

# Prueba de humo con el modelo (2 escenarios, 2 configs) — comprueba que Ollama responde
make campaign-fast

# Campaña completa: C0/C1/C2 × S1–S4 + 50 tareas benignas  (~3–4 h según tu notas)
make campaign

# Tablas, gráfica y tabla LaTeX para la memoria
make report memoria-figs
make memoria          # compila memoria/memoria.pdf con los resultados reales
open results/asr.png
```

Resultados en `results/`: `runs.jsonl` (traza completa), `summary.csv`, `asr.csv`, `asr.png`,
`telemetry.jsonl` (base para reglas de detección).

---

## 5. Rutina de trabajo recomendada (regla de las horas)

Cada sesión conmigo (Claude):
1. Empieza pidiendo **un entregable cerrado** ("hoy: capítulo 4 redactado" / "hoy: escenario 5 añadido").
2. Al terminar, añade una línea a `CHANGELOG.md` con las horas: `### 2026-10-06 — Forense + scaffold [3h]`.
3. Si en la semana 7 (20 dic) la suma proyectada supera 60 h → baja a 3 escenarios y 3 controles
   **sin cambiar título ni índice** (la norma de los 15 días queda a salvo).

---

## 6. Qué mandar a la encuesta del 29 de octubre

Ya está redactado en tu documento de propuestas del Proyecto (opción, título, índice y descripción listos
para pegar). El repo de esta guía es el anexo de código; enlázalo cuando esté público.

---

## 7. Orden de los capítulos vs. el código

| Capítulo de la memoria | Se apoya en |
|---|---|
| 4. Modelo de amenazas | `docs/threat-model/` (DFD + matriz) |
| 5. Laboratorio | `src/tfm_lab/` (agente, tools, lab) |
| 6. Escenarios y línea base | `src/tfm_lab/attacks/`, `results/` (C0) |
| 7. Arquitectura de referencia | `src/tfm_lab/controls/`, `config/policy.yaml` |
| 8. Validación | `results/asr.png`, `asr.csv` (C1/C2) |
| 9. Gobierno | `results/telemetry.jsonl` + ADRs |

---

## Resolución de problemas

- **`ollama` no responde** → `ollama serve` en otra terminal; comprueba `OLLAMA_HOST`.
- **Guardrail pide licencia** → usa el modelo de ProtectAI (variable `TFM_GUARD_MODEL`).
- **Poca RAM / lento** → `qwen3:4b`, reduce `num_ctx` a 4096, o usa `--scenarios S1 S4`.
- **Quiero desarrollar sin gastar batería en el modelo** → `TFM_GUARD_BACKEND=heuristic` + `--dry-run`.
