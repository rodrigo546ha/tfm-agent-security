# Solo para reproducibilidad en Linux/VM (CPU). En el Mac se usa Ollama nativo, sin Docker.
FROM python:3.12-slim
RUN pip install --no-cache-dir uv
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN uv pip install --system -e ".[dev]"
COPY . .
CMD ["make", "reproduce"]
