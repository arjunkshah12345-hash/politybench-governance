# syntax=docker/dockerfile:1
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md BENCHMARK_SPEC.md LICENSE CITATION.cff ./
COPY packages ./packages
COPY calibration ./calibration
COPY configs ./configs
COPY scripts ./scripts
RUN pip install --no-cache-dir -e ".[dev]"
ENV PYTHONUNBUFFERED=1
CMD ["politybench", "benchmark-smoke", "--fidelity", "F0", "--seeds", "2"]
