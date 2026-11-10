PYTHON ?= python
BACKEND = cd backend &&

.PHONY: backend frontend test lint format migrate db-check import search

backend:
	$(BACKEND) uvicorn app.main:app --reload

frontend:
	cd frontend && npm run dev

test:
	$(BACKEND) pytest -q
	cd frontend && npm run build

lint:
	$(BACKEND) ruff check app tests alembic ingestion && ruff format --check app tests alembic ingestion
	cd frontend && npm run lint && npm run format:check

migrate:
	$(BACKEND) alembic upgrade head

db-check:
	$(BACKEND) $(PYTHON) -m ingestion.check_db

# make import FILE=data/example.json
import:
	$(BACKEND) $(PYTHON) -m ingestion.import_document --file ../$(FILE)

# make search Q="Perfect Roe"
search:
	$(BACKEND) $(PYTHON) -m ingestion.search "$(Q)"
