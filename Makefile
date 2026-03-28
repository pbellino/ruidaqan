NAME = ruidaqan

.SUFFIXES:
.PHONY: clean dist install install_dev docs lint test

HASH := $(shell git rev-parse HEAD)

# ── Instalación ──────────────────────────────────────────────────────────────

install:
	python -m pip install -e .

install_dev:
	python -m pip install -e ".[dev,build]"

uninstall:
	python -m pip uninstall $(NAME)

# ── Calidad de código ─────────────────────────────────────────────────────────

lint:
	ruff check src/ tests/

lint_fix:
	ruff check --fix src/ tests/

# ── Tests ─────────────────────────────────────────────────────────────────────

test:
	pytest

test_cov:
	pytest --cov=src/ruidaqan --cov-report=term-missing

# ── Documentación ─────────────────────────────────────────────────────────────

docs:
	$(MAKE) -C docs html

# ── Distribución ──────────────────────────────────────────────────────────────

dist: docs
	cp -r docs/_build/html src/ruidaqan/docs/
	sed -i -e 's/__commit__ =.*/__commit__ = "$(HASH)"/g' src/ruidaqan/__init__.py
	sed -i -e 's/DEBUG_MODE =.*/DEBUG_MODE = False/g'       src/ruidaqan/gui/config.py
	sed -i -e 's/DATA_FOLDER =.*/DATA_FOLDER = ""/g'        src/ruidaqan/gui/config.py
	python -m build
	git restore src/ruidaqan/__init__.py src/ruidaqan/gui/config.py

clean:
	rm -fr dist build src/*.egg-info
