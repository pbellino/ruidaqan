NAME = ruidaqan

.SUFFIXES:
.PHONY: clean dist install install_dev docs capturas lint test exe exe_adquisicion \
        exe_procesamiento exe_resultados


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

# Regenera las capturas de procesamiento y resultados (docs/manual/images)
# con una serie sintética, sin pantalla ni placa
capturas:
	python docs/genera_capturas.py

# Paquete instalable con la documentación y el hash del commit estampado.
# La lógica está en scripts/empaqueta.py para que funcione también con el
# make de Windows (sin mkdir -p, cp, sed ni git restore).
# Detrás de un proxy o sin conexión: make dist OPC=--sin-aislamiento
OPC ?=

dist:
	python scripts/empaqueta.py dist $(OPC)

clean:
	python scripts/empaqueta.py limpia

# Ejecutables con PyInstaller (también arma el paquete)
exe:
	python scripts/empaqueta.py exe $(OPC)

exe_adquisicion exe_procesamiento exe_resultados:
	python scripts/empaqueta.py exe $(subst exe_,,$@) $(OPC)
