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

docs:
	$(MAKE) -C docs html

# ── Distribución ──────────────────────────────────────────────────────────────

dist: docs
	# Sincronizamos la documentación generada dentro del paquete
	mkdir -p src/ruidaqan/docs/
	cp -r docs/_build/html/* src/ruidaqan/docs/
	
	# Seteamos configuración de producción para la GUI
	sed -i -e 's/DEBUG_MODE =.*/DEBUG_MODE = False/g'       src/ruidaqan/gui/config.py
	sed -i -e 's/DATA_FOLDER =.*/DATA_FOLDER = ""/g'        src/ruidaqan/gui/config.py
	
	# Construimos el paquete
	python -m build
	
	# Restauramos los archivos modificados para no ensuciar el repo local
	git restore src/ruidaqan/gui/config.py

clean:
	rm -fr dist build src/*.egg-info
