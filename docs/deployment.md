# Guía de despliegue y reproducibilidad

## En el Mac (equipo principal)
1. `ollama pull qwen3:8b` y anota el digest en `config/lab.yaml`.
2. `make setup` (uv venv + dependencias + `requirements.txt`).
3. Guardrail real: acepta la licencia de Llama Prompt Guard 2 en Hugging Face y `huggingface-cli login`
   (o usa `TFM_GUARD_MODEL=protectai/deberta-v3-base-prompt-injection-v2`, sin licencia).
4. `make reproduce`. Resultados en `results/`.

## Reproducción en VM limpia (verificación del capítulo 8)
1. VirtualBox con Ubuntu, o cuenta de usuario nueva en el Mac.
2. `docker compose up` (CPU) o repetir los pasos anteriores.
3. Comparar `results/asr.csv` con el commit de referencia: el ASR debe coincidir en las filas deterministas
   (S2/S3 con controles) y quedar dentro de ±1 variante en las dependientes del muestreo del modelo.

## Checklist de entrega (tutores)
- [ ] Repo público accesible, `make reproduce` funciona desde cero.
- [ ] `results/asr.png` y `results/asr.csv` regenerados.
- [ ] Vídeo <5 min, MP4/MKV <50 MB.
- [ ] Memoria <= 20 caras (sin portada/índice).
