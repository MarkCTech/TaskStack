# Used by scripts/build_frontend.py (reads these lines)
FRONTEND_REPO := https://github.com/MarkCTech/user_todos.git
FRONTEND_BRANCH := master

VENV ?= .venv

ifeq ($(OS),Windows_NT)
PYTHON ?= python
BIN := $(VENV)/Scripts
else
PYTHON ?= python3
BIN := $(VENV)/bin
endif

PYTEST := $(BIN)/pytest
RUFF := $(BIN)/ruff
PY := $(BIN)/python

.PHONY: help lint test ci clean

help:
	@echo "Expects .venv already created and deps installed (see README Step 1–2)."
	@echo "make ci     - lint + test"
	@echo "make clean  - remove .venv and pytest/ruff caches"

lint:
	$(RUFF) check .
	$(PY) -m compileall -q main.py tests

test:
	$(PYTEST) -q

ci: lint test

clean:
	$(PYTHON) -c "import shutil, pathlib; p=pathlib.Path('.'); shutil.rmtree(p/'$(VENV)', ignore_errors=True); shutil.rmtree(p/'.pytest_cache', ignore_errors=True); shutil.rmtree(p/'.ruff_cache', ignore_errors=True)"
