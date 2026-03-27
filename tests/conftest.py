"""
Configuración global de pytest.

Los archivos de datos de prueba (.h5, .RUI, .pkl) deben copiarse
manualmente en tests/fixtures/ antes de correr los tests, o pueden
descargarse con:

    make download_fixtures   (ver Makefile)

Están excluidos del repo (.gitignore) por su tamaño.
"""

import pytest
from pathlib import Path

# Directorio base de fixtures de datos
FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir():
    """Retorna el Path al directorio de fixtures."""
    return FIXTURES_DIR


@pytest.fixture
def hdf5_file(fixtures_dir):
    p = fixtures_dir / "S001-N2-1.h5"
    if not p.exists():
        pytest.skip(f"Fixture no disponible: {p}. Copiá el archivo a tests/fixtures/")
    return str(p)


@pytest.fixture
def rui_file(fixtures_dir):
    p = fixtures_dir / "S31-N3-1.RUI"
    if not p.exists():
        pytest.skip(f"Fixture no disponible: {p}. Copiá el archivo a tests/fixtures/")
    return str(p)


@pytest.fixture
def fit_results_file(fixtures_dir):
    p = fixtures_dir / "S001-resultados_ajustes.pkl"
    if not p.exists():
        pytest.skip(f"Fixture no disponible: {p}. Copiá el archivo a tests/fixtures/")
    return str(p)
