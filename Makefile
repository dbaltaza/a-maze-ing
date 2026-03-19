VENV_NAME = .venv

PYTHON = $(VENV_NAME)/bin/python3
PIP = $(VENV_NAME)/bin/pip

MAIN_FILE = a_maze_ing.py
CONFIG_FILE = config.txt
REQ_FILE = requirements.txt
OUTPUTS = outputs/

all: install run

build: $(VENV_NAME)/bin/activate

install: $(VENV_NAME)/bin/activate $(OUTPUTS)

$(OUTPUTS):
	mkdir -p $(OUTPUTS)

$(VENV_NAME)/bin/activate: $(REQ_FILE)
	@echo "Creating virtual environment and installing required dependencies..."
	python3 -m venv $(VENV_NAME)
	$(PIP) install --upgrade pip
	$(PIP) install -r $(REQ_FILE)
	$(PIP) install .
	touch $(VENV_NAME)/bin/activate

run: install
	@echo "Running..."
	$(PYTHON) $(MAIN_FILE) $(CONFIG_FILE)

debug: install
	@echo "debugging..."
	$(PYTHON) -m pdb $(MAIN_FILE) $(CONFIG_FILE)

lint: install
	@echo "Linting..."
	@echo "Flake8: "
	$(PYTHON) -m flake8 $(MAIN_FILE) app mazegen tests
	@echo "Mypy: "
	$(PYTHON) -m mypy $(MAIN_FILE) app mazegen tests --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict: install
	@echo "Linting strictly..."
	@echo "Flake8: "
	$(PYTHON) -m flake8 $(MAIN_FILE) app mazegen tests
	@echo "Mypy: "
	$(PYTHON) -m mypy $(MAIN_FILE) app mazegen tests --strict

clean:
	@echo "Cleaning temporary files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@rm -rf outputs/
	@rm -rf .mypy_cache
	@rm -rf .pytest_cache
	@rm -rf build
	@rm -rf dist
	@rm -rf *.egg-info
	@rm -rf $(VENV_NAME)

.PHONY: all build install run debug clean lint lint-strict
