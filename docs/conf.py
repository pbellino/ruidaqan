import os
import sys
import subprocess
import datetime
import unittest.mock

# -- Mocking de dependencias pesadas para evitar errores de Qt/libEGL en CI ----
MOCK_MODULES = [
    'PyQt5', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets', 
    'PyQt5.QtWebEngineWidgets', 'numpy', 'pandas', 'matplotlib', 
    'matplotlib.pyplot', 'pyqtgraph', 'PyQt5.QtChart'
]
for mod_name in MOCK_MODULES:
    sys.modules[mod_name] = unittest.mock.Mock()

# -- Configuración de rutas para autodoc -------------------------------------
sys.path.insert(0, os.path.abspath('../src'))

# -- Extracción de Versión y Hash de Git -------------------------------------
try:
    try:
        import tomllib as tomli  # Python 3.11+
    except ImportError:
        import tomli

    pyproject_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pyproject.toml"))
    with open(pyproject_path, "rb") as f:
        pyproject = tomli.load(f)
        pkg_version = pyproject.get("project", {}).get("version", "0.0.0")
except Exception:
    pkg_version = "0.0.0"

try:
    git_hash = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode('ascii').strip()
except Exception:
    git_hash = "unknown"

# -- Project information -----------------------------------------------------
project = 'RuiDAQAn'
current_year = datetime.date.today().year
copyright = f'2023-{current_year}, División Física Experimental de Reactores'
author = 'División Física Experimental de Reactores'

# Release incluye versión + hash para trazabilidad técnica
release = f'{pkg_version} ({git_hash})'
version = pkg_version

# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx_design',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']
language = 'es'

# -- Options for HTML output -------------------------------------------------
html_theme = 'pydata_sphinx_theme'
html_static_path = ['_static']

# Esto evita que autodoc falle si no encuentra los módulos de la GUI realmente
autodoc_mock_imports = MOCK_MODULES
