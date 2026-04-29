FROM python:3.11-slim

# Récupérer le binaire uv depuis l'image officielle Astral
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

# Outils nécessaires pour télécharger les assets
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# === Installer les deps Python (couche cachée) ===
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# === Télécharger le modèle ML depuis le release GitHub ===
ARG GITHUB_REPO
ARG RELEASE_TAG
ARG MODEL_SHA256

RUN test -n "$GITHUB_REPO" || (echo "GITHUB_REPO build arg required" && exit 1) && \
    test -n "$RELEASE_TAG" || (echo "RELEASE_TAG build arg required" && exit 1) && \
    mkdir -p /app/models && \
    curl -fL -o /tmp/model.tar.gz \
      "https://github.com/${GITHUB_REPO}/releases/download/${RELEASE_TAG}/minilm-multilingual.tar.gz" && \
    if [ -n "$MODEL_SHA256" ]; then \
        echo "${MODEL_SHA256}  /tmp/model.tar.gz" | sha256sum -c - ; \
    fi && \
    tar xzf /tmp/model.tar.gz -C /app/models && \
    rm /tmp/model.tar.gz

ENV PATH="/app/.venv/bin:$PATH" \
    MODEL_PATH=/app/models/minilm-multilingual

# Sanity check : le modèle se charge bien
RUN python -c "from sentence_transformers import SentenceTransformer; \
    m = SentenceTransformer('/app/models/minilm-multilingual'); \
    print('Model loaded OK, dim =', m.get_sentence_embedding_dimension())"