FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy

# System dependencies for OCR and PDF rendering
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        ghostscript \
        poppler-utils \
        tesseract-ocr \
        tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# Install uv (pinned tag; avoid :latest)
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv

RUN groupadd --gid 10001 pulp \
    && useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin pulp \
    && mkdir -p /app \
    && chown -R pulp:pulp /app

WORKDIR /app

COPY --chown=10001:10001 pyproject.toml uv.lock README.md cli.py ./
COPY --chown=10001:10001 src/ ./src/

USER pulp
RUN uv sync --frozen --no-dev --no-editable

ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT ["pulp"]
