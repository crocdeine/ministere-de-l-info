# syntax=docker/dockerfile:1.7

# ============================================================
# Stage 1 — Builder : install Python deps avec uv
# ============================================================
FROM python:3.12-slim-bookworm AS builder

# Install uv depuis l'image officielle Astral
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Dépendances système nécessaires à GeoPandas (GDAL) et build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copier les manifestes de dépendances en premier (cache layer)
COPY pyproject.toml uv.lock ./

# Installer les dépendances dans un venv système (sans le projet lui-même)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Copier le code et installer le package
COPY src ./src
COPY app.py ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ============================================================
# Stage 2 — Runtime : image finale légère
# ============================================================
FROM python:3.12-slim-bookworm AS runtime

# Dépendances runtime minimales (GDAL pour GeoPandas, curl pour healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgdal32 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Installer Tectonic (compilateur LaTeX moderne, ~50 Mo)
RUN curl --proto '=https' --tlsv1.2 -fsSL https://drop-sh.fullyjustified.net | sh \
    && mv tectonic /usr/local/bin/ \
    && tectonic --version

# Créer un utilisateur non-root pour la sécurité
RUN groupadd --system --gid 1000 app \
    && useradd --system --uid 1000 --gid app --create-home app

WORKDIR /app

# Copier le venv et le code depuis le builder
COPY --from=builder --chown=app:app /app /app

# Mettre le venv dans le PATH
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

USER app

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "app.py"]
