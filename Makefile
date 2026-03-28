NAME = ruidaqan

.SUFFIXES:
.PHONY: clean dist install install_dev docs lint test

# ── Instalación ──────────────────────────────────────────────────────────────

install:
	python -m pip install .

install_dev:
	python -m pip install -e ".[dev,docs,build]"

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

dist: docs
	# 1. Preparar carpeta de docs interna
	mkdir -p src/ruidaqan/docs/
	cp -r docs/_build/html/* src/ruidaqan/docs/

	# 2. Configuración de producción (GUI y Commit Hash)
	sed -i -e 's/DEBUG_MODE =.*/DEBUG_MODE = False/g'   src/ruidaqan/gui/config.py
	sed -i -e 's/DATA_FOLDER =.*/DATA_FOLDER = ""/g'    src/ruidaqan/gui/config.py

	# El estampado con el ancla ^ para evitar el IndentationError
	$(eval HASH=$(shell git rev-parse --short HEAD))
	sed -i 's/^__commit__ =.*/__commit__ = "$(HASH)"/' src/ruidaqan/__init__.py

	# 3. Construir paquete
	python -m build

	# 4. Limpiar para que tu repo local siga igual
	git restore src/ruidaqan/gui/config.py src/ruidaqan/__init__.py

clean:
	rm -fr dist build src/*.egg-info
