NAME = ruidaqan

.SUFFIXES:
.PHONY: clean dist install install_dev docs lint test exe exe_adquisicion \
        exe_procesamiento exe_resultados stamp_hash restore_hash

# Variables de ruta
INIT_FILE = src/ruidaqan/__init__.py
MAKE_EXE = make -f pyinstaller/Makefile.exe

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

dist: docs
	# 1. Preparar carpeta de docs interna
	mkdir -p src/ruidaqan/docs/html/
	cp -r docs/_build/html/* src/ruidaqan/docs/html/

	# 2. Configuración de producción (GUI y Commit Hash)
	sed -i -e 's/DEBUG_MODE =.*/DEBUG_MODE = False/g'   src/ruidaqan/gui/config.py

	# El estampado con el ancla ^ para evitar el IndentationError
	$(eval HASH=$(shell git rev-parse --short HEAD))
	sed -i 's/^__commit__ =.*/__commit__ = "$(HASH)"/' src/ruidaqan/__init__.py

	# 3. Construir paquete
	python -m build

	# 4. Limpiar para que tu repo local siga igual
	git restore src/ruidaqan/gui/config.py src/ruidaqan/__init__.py

clean:
	rm -fr dist build src/*.egg-info

# Construye todo el ecosistema de distribución
# Nota: 'dist' ya hace su propio stamp/restore interno.

exe_adquisicion exe_procesamiento exe_resultados: dist stamp_hash
	$(MAKE_EXE) $@
	@$(MAKE) restore_hash
	@echo "Ejecutable $@ generado y repo restaurado."

exe: dist
	@$(MAKE) stamp_hash
	@echo "Generando ejecutables independientes..."
	$(MAKE_EXE) exe_adquisicion
	$(MAKE_EXE) exe_procesamiento
	$(MAKE_EXE) exe_resultados
	@$(MAKE) restore_hash
	@echo "Proceso de ejecutables finalizado y repo limpio."

stamp_hash:
	$(eval HASH=$(shell git rev-parse --short HEAD))
	@echo "Estampando hash $(HASH) en $(INIT_FILE)..."
	sed -i 's/^__commit__ =.*/__commit__ = "$(HASH)"/' $(INIT_FILE)

restore_hash:
	@echo "Restaurando $(INIT_FILE) al estado original..."
	git restore $(INIT_FILE)
