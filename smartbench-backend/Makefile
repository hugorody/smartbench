SHELL := /bin/bash

.PHONY: install dev lint run up down reset verify migrate seed test smoke homologate

install:
	python -m pip install --upgrade pip
	pip install -e .[dev]

dev:
	flask --app app:create_app --debug run --host 0.0.0.0 --port 8000

lint:
	ruff check app tests scripts

run:
	gunicorn -b 0.0.0.0:8000 'app:create_app()'

up:
	docker compose up -d --build

down:
	docker compose down --remove-orphans

reset:
	./scripts/reset_local_stack.sh

verify:
	./scripts/verify_env.sh

migrate:
	./scripts/db_upgrade.sh

seed:
	./scripts/db_seed.sh

test:
	docker compose exec -T web python -m pytest

smoke:
	./scripts/smoke_api.sh

homologate:
	docker compose up -d --build
	./scripts/verify_env.sh
	./scripts/db_upgrade.sh
	./scripts/db_seed.sh
	docker compose exec -T web python -m pytest
	./scripts/smoke_api.sh
	@echo "[homologate] End-to-end homologation completed successfully."
