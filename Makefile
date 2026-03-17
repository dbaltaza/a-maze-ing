PYTHON ?= python3
APP ?= a_maze_ing.py
CONFIG ?= config.txt

.DEFAULT_GOAL := help

.PHONY: help install run debug clean lint lint-strict

help:
	@printf "\nA-Maze-ing\n\n"
	@printf "  %-12s %s\n" "make run" "Run the maze app with \`$(CONFIG)\`"
	@printf "  %-12s %s\n" "make debug" "Run the app in pdb"
	@printf "  %-12s %s\n" "make install" "Install project and dev tools"
	@printf "  %-12s %s\n" "make lint" "Run flake8 and mypy"
	@printf "  %-12s %s\n" "make lint-strict" "Run flake8 and strict mypy"
	@printf "  %-12s %s\n" "make clean" "Remove build and cache artifacts"
	@printf "\n"

install:
	@printf "\n[install] updating environment\n"
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install .
	$(PYTHON) -m pip install build flake8 mypy

run:
	@printf "\n[run] launching maze with %s\n" "$(CONFIG)"
	$(PYTHON) $(APP) $(CONFIG)

debug:
	@printf "\n[debug] starting pdb with %s\n" "$(CONFIG)"
	$(PYTHON) -m pdb $(APP) $(CONFIG)

clean:
	@printf "\n[clean] removing generated caches and build artifacts\n"
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -prune -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -prune -exec rm -rf {} +
	rm -rf build dist *.egg-info

lint:
	@printf "\n[lint] running static checks\n"
	$(PYTHON) -m flake8 .
	$(PYTHON) -m mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	@printf "\n[lint-strict] running strict static checks\n"
	$(PYTHON) -m flake8 .
	$(PYTHON) -m mypy . --strict
