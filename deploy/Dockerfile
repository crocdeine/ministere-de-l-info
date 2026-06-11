FROM python:3.12-slim

# uv depuis l'image officielle
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

WORKDIR /app

# Couche dépendances (cache Docker invalidé seulement si uv.lock change)
# README.md requis par pyproject.toml pour le build du paquet
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

# Code source (cache invalidé seulement si le code change)
COPY src/ ./src/
COPY pages/ ./pages/
COPY app.py ./

# Installer le paquet local en mode éditable (path resolution via parents[3] reste valide)
RUN uv sync --frozen --no-dev

# Pré-installation de l'extension DuckDB spatial
# L'extension est téléchargée au build time et incluse dans l'image,
# évitant le téléchargement au runtime dans un container éphémère.
RUN uv run python -c "import duckdb; con = duckdb.connect(); con.execute('INSTALL spatial'); con.close()"

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["uv", "run", "streamlit", "run", "app.py", \
     "--server.address", "0.0.0.0", \
     "--server.headless", "true", \
     "--server.port", "8501"]
