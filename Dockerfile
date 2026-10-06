# syntax=docker/dockerfile:1.7

# ============================================================
# Stage 1 — Builder : install Python deps avec uv
# ============================================================
# python:3.12-slim-bookworm (index multi-arch amd64+arm64, relevé le 2026-10-06)
FROM python:3.12-slim-bookworm@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258 AS builder

# Install uv depuis l'image officielle Astral
COPY --from=ghcr.io/astral-sh/uv:0.11.16 /uv /uvx /bin/

# Dépendances système nécessaires à GeoPandas (GDAL) et build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

ENV UV_LINK_MODE=copy

WORKDIR /app

# Copier les manifestes de dépendances en premier (cache layer)
COPY pyproject.toml uv.lock ./

# Installer les dépendances dans un venv système (sans le projet lui-même)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Copier le code et installer le package
COPY src ./src
COPY pages ./pages
COPY README.md ./
COPY app.py ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ============================================================
# Stage 2 — Runtime : image finale légère
# ============================================================
# python:3.12-slim-bookworm (index multi-arch amd64+arm64, relevé le 2026-10-06)
FROM python:3.12-slim-bookworm@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258 AS runtime

# Dépendances runtime minimales (GDAL pour GeoPandas, curl pour healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgdal32 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Installer Tectonic (compilateur LaTeX moderne, binaire statique ~50 Mo)
# Détection d'architecture : Apple Silicon = aarch64, Intel = x86_64
# SHA256 : empreintes publiées par GitHub (champ "digest") pour les assets de la release
# tectonic@0.16.9 (https://github.com/tectonic-typesetting/tectonic/releases/tag/tectonic%400.16.9).
# Le projet ne publie pas de fichier de somme séparé. À remettre à jour avec la version.
ARG TECTONIC_VERSION=0.16.9
ARG TECTONIC_SHA256_X86_64=60b13a0826ae7ad9ce34b4a2df06bff2cfcfa6dda8a915477c0cbb84e1a4a902
ARG TECTONIC_SHA256_AARCH64=f9aa39017dbd51f111fdb93dda222178cbe51c8193508fc567b523cc74fff9c1
RUN ARCH=$(uname -m) \
    && case "$ARCH" in \
        x86_64) TARGET="x86_64-unknown-linux-musl"; SHA="$TECTONIC_SHA256_X86_64" ;; \
        aarch64) TARGET="aarch64-unknown-linux-musl"; SHA="$TECTONIC_SHA256_AARCH64" ;; \
        *) echo "Architecture non supportée: $ARCH" && exit 1 ;; \
    esac \
    && curl --proto '=https' --tlsv1.2 -fsSL \
        "https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic%40${TECTONIC_VERSION}/tectonic-${TECTONIC_VERSION}-${TARGET}.tar.gz" \
        -o /tmp/tectonic.tar.gz \
    && echo "$SHA  /tmp/tectonic.tar.gz" | sha256sum -c - \
    && tar -xzf /tmp/tectonic.tar.gz -C /tmp \
    && mv /tmp/tectonic /usr/local/bin/ \
    && rm /tmp/tectonic.tar.gz \
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

# Skip Streamlit email prompt au premier démarrage
RUN mkdir -p /home/app/.streamlit \
    && echo '[general]' > /home/app/.streamlit/credentials.toml \
    && echo 'email = ""' >> /home/app/.streamlit/credentials.toml \
    && chown -R app:app /home/app/.streamlit

USER app

# Pré-installation des extensions DuckDB nécessaires (évite le téléchargement runtime)
RUN python -c "import duckdb; con = duckdb.connect(':memory:'); con.execute('INSTALL spatial')"

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "app.py"]
