PYTHON ?= .venv/bin/python
PYTEST ?= .venv/bin/pytest
UVICORN ?= .venv/bin/uvicorn
export PYTHONPATH := src

.PHONY: test api web

test:
	$(PYTEST)

api:
	$(UVICORN) api.main:app --host 0.0.0.0 --port 8000

web:
	cd frontend && npm run dev -- --host 0.0.0.0 --port 5173
