.PHONY: install backend frontend test lint typecheck fmt demo demo-reset demo-smoke up ci

PYTHON := backend/.venv/bin/python
PYTEST := backend/.venv/bin/pytest
RUFF := backend/.venv/bin/ruff
MYPY := backend/.venv/bin/mypy

install:
	cd backend && uv venv --python 3.12 .venv || true
	cd backend && uv pip install -e ".[dev]"
	cd frontend && npm install

backend:
	cd backend && .venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

frontend:
	cd frontend && npm run dev

up:
	docker compose up --build

demo-reset:
	curl -sS -X POST http://127.0.0.1:8000/demo/reset | python3 -m json.tool

demo:
	@echo "Backend: http://127.0.0.1:8000/docs"
	@echo "Frontend: http://127.0.0.1:3000"
	@echo "Then paste the demo command into the console."

fmt:
	cd backend && $(RUFF) format app tests

lint:
	cd backend && $(RUFF) check app tests
	cd frontend && npm run lint || true

typecheck:
	cd backend && $(MYPY) app tests
	cd frontend && npm run typecheck

test:
	cd backend && $(PYTEST) -q

demo-smoke:
	cd backend && .venv/bin/python ../scripts/demo_smoke.py

ci: fmt lint typecheck test demo-smoke
