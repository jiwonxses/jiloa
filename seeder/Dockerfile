FROM movie-app-base:latest

WORKDIR /app

# === Télécharger les CSV depuis le release GitHub ===
ARG GITHUB_REPO
ARG RELEASE_TAG

RUN test -n "$GITHUB_REPO" || (echo "GITHUB_REPO build arg required" && exit 1) && \
    test -n "$RELEASE_TAG" || (echo "RELEASE_TAG build arg required" && exit 1) && \
    mkdir -p /data && cd /data && \
    for f in movies_metadata.csv credits.csv keywords.csv link.csv tag.csv; do \
        curl -fL -O "https://github.com/${GITHUB_REPO}/releases/download/${RELEASE_TAG}/${f}"; \
    done

# === Code du seeder ===
COPY importer_donnees.py ./

ENV DATA_DIR=/data
# MODEL_PATH est déjà défini par la base image

CMD ["python", "-u", "importer_donnees.py"]