PYTHON ?= python3
APP ?= a_maze_ing.py
CONFIG ?= config.txt

.PHONY: install run debug clean lint

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install .
	$(PYTHON) -m pip install flake8 mypy

run:
	$(PYTHON) $(APP) $(CONFIG)

debug:
	$(PYTHON) -m pdb $(APP) $(CONFIG)

clean:
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -prune -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -prune -exec rm -rf {} +
	rm -rf build dist *.egg-info

lint:
	flake8 .
	mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs
