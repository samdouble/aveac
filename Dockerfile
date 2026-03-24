FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir /output

WORKDIR /app

COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen

COPY src/ src/

CMD ["uv", "run", "src/main.py"]
