PYTHON ?= python3
VENV ?= .venv
VENV_PYTHON := $(VENV)/bin/python
APP ?= a_maze_ing.py
CONFIG ?= config.txt

.DEFAULT_GOAL := help

.PHONY: help build install run debug clean lint lint-strict

$(VENV_PYTHON):
	@printf "\n[build] creating virtual environment in %s\n" "$(VENV)"
	$(PYTHON) -m venv $(VENV)
	@printf "[build] virtual environment ready\n"

build: $(VENV_PYTHON)
	@printf "[build] activate with: source %s/bin/activate\n" "$(VENV)"

help:
	@printf "\nA-Maze-ing\n\n"
	@printf "  %-12s %s\n" "make build" "Create .venv if missing"
	@printf "  %-12s %s\n" "make run" "Run the maze app with \`$(CONFIG)\`"
	@printf "  %-12s %s\n" "make debug" "Run the app in pdb"
	@printf "  %-12s %s\n" "make install" "Install project and dev tools into .venv"
	@printf "  %-12s %s\n" "make lint" "Run flake8 and mypy"
	@printf "  %-12s %s\n" "make lint-strict" "Run flake8 and strict mypy"
	@printf "  %-12s %s\n" "make clean" "Remove build and cache artifacts"
	@printf "\n"

install: build
	@printf "\n[install] updating environment\n"
	$(VENV_PYTHON) -m pip install --upgrade pip
	$(VENV_PYTHON) -m pip install .
	$(VENV_PYTHON) -m pip install build flake8 mypy

run: build
	@printf "\n[run] launching maze with %s\n" "$(CONFIG)"
	$(VENV_PYTHON) $(APP) $(CONFIG)

debug: build
	@printf "\n[debug] starting pdb with %s\n" "$(CONFIG)"
	$(VENV_PYTHON) -m pdb $(APP) $(CONFIG)

clean:
	@printf "\n[clean] removing generated caches and build artifacts\n"
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -prune -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -prune -exec rm -rf {} +
	rm -rf build dist *.egg-info

lint: build
	@printf "\n[lint] running static checks\n"
	$(VENV_PYTHON) -m flake8 .
	$(VENV_PYTHON) -m mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict: build
	@printf "\n[lint-strict] running strict static checks\n"
	$(VENV_PYTHON) -m flake8 .
	$(VENV_PYTHON) -m mypy . --strict
