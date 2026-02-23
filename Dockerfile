# ─────────────────────────────────────────────
# Atlas MCP Server — multi-stage Docker build
# ─────────────────────────────────────────────

# ── Stage 1: build ──────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first (layer caching)
COPY pyproject.toml uv.lock* README.md ./
COPY src/ src/

# Create virtualenv and install production dependencies only
RUN uv venv /opt/venv \
    && VIRTUAL_ENV=/opt/venv uv pip install --no-cache .

# ── Stage 2: runtime ───────────────────────
FROM python:3.12-slim AS runtime

LABEL maintainer="jhow-043" \
      description="Atlas MCP Server — structured context and RAG for LLM agents" \
      org.opencontainers.image.source="https://github.com/jhow-043/Atlas-MCP"

# Non-root user for security
RUN groupadd --gid 1000 atlas \
    && useradd --uid 1000 --gid atlas --create-home atlas

WORKDIR /app

# Copy virtualenv from builder
COPY --from=builder /opt/venv /opt/venv

# Ensure venv is used
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Default environment variables
ENV ATLAS_TRANSPORT="stdio" \
    ATLAS_LOG_LEVEL="INFO" \
    ATLAS_LOG_FORMAT="json" \
    POSTGRES_HOST="postgres" \
    POSTGRES_PORT="5432" \
    POSTGRES_USER="atlas" \
    POSTGRES_DB="atlas_mcp"

USER atlas

ENTRYPOINT ["python", "-m", "atlas_mcp"]
CMD ["--transport", "stdio"]
