.PHONY: help base build up down logs clean reset

# Charge automatiquement les variables de .env
include .env
export

help:
	@echo "Targets:"
	@echo "  make base    - Build l'image de base partagée (à faire en premier)"
	@echo "  make build   - Build les services (db, seeder)"
	@echo "  make up      - Lance toute la stack"
	@echo "  make down    - Stoppe la stack (garde les données)"
	@echo "  make logs    - Affiche les logs en suivi"
	@echo "  make clean   - Stoppe + supprime images des services (garde les données)"
	@echo "  make reset   - Stoppe + supprime tout y compris les données DB"

base:
	docker build \
		--build-arg GITHUB_REPO=$(GITHUB_REPO) \
		--build-arg RELEASE_TAG=$(RELEASE_TAG) \
		--build-arg MODEL_SHA256=$(MODEL_SHA256) \
		-t movie-app-base:latest \
		./base

backend-logs:
	docker compose logs -f backend

backend-shell:
	docker compose exec backend bash

api-docs:
	@echo "Ouvre http://localhost:8000/docs dans ton navigateur"

build-frontend:
	docker compose build frontend

up-frontend:
	docker compose up -d frontend

logs-frontend:
	docker compose logs -f frontend

test:
	docker compose -f docker-compose.test.yml up -d --build
	@echo "Attente démarrage stack test (peut prendre 2-3 min pour la vectorisation)..."
	@bash -c 'until curl -sf http://localhost:8001/health > /dev/null; do sleep 5; echo "  ...still waiting"; done'
	cd backend && uv run pytest tests/test_api.py -v
	docker compose -f docker-compose.test.yml down

test-stack-up:
	docker compose -f docker-compose.test.yml up -d --build

test-stack-down:
	docker compose -f docker-compose.test.yml down

build: base
	docker compose build

up: build
	docker compose up

down:
	docker compose down

logs:
	docker compose logs -f

clean:
	docker compose down --rmi local

reset:
	docker compose down -v --rmi local
	docker rmi movie-app-base:latest 2>/dev/null || true