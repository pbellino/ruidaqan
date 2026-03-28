import os
import sys
import subprocess
import datetime

# -- Configuración de rutas para autodoc -------------------------------------
# Aseguramos que Sphinx encuentre el código fuente en src/
sys.path.insert(0, os.path.abspath('../src'))

# -- Extracción de Versión y Hash --------------------------------------------
try:
    # Intentamos importar el paquete directamente. 
    # Si el Makefile o el CI ya corrieron el "sed", esto leerá los valores reales.
    import ruidaqan
    pkg_version = getattr(ruidaqan, "__version__", "0.0.0")
    git_hash = getattr(ruidaqan, "__commit__", "")
except ImportError:
    pkg_version = "0.0.0"
    git_hash = ""

# Si el hash está vacío (no estampado), intentamos obtenerlo de Git
if not git_hash or git_hash == "":
    try:
        git_hash = subprocess.check_output(['git', 'rev-parse', '--short', HEAD]).decode('ascii').strip()
    except Exception:
        git_hash = "unknown"

# -- Project information -----------------------------------------------------
project = 'RuiDAQAn'
current_year = datetime.date.today().year
copyright = f'2023-{current_year}, División Física Experimental de Reactores'
author = 'División Física Experimental de Reactores'

# Si el hash es 'unknown' o vacío, no lo mostramos en la release
release = f'{pkg_version} ({git_hash})' if git_hash and git_hash != "unknown" else pkg_version
version = pkg_version

# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx_design',
]

# Mock de imports para evitar dependencias pesadas o de sistema en el build
autodoc_mock_imports = [
    'PyQt5', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets', 
    'PyQt5.QtWebEngineWidgets', 'PyQt5.QtChart', 'pyqtgraph',
    'numpy', 'pandas', 'matplotlib', 'tables', 'scipy', 'nidaqmx'
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']
language = 'es'
html_theme = 'pydata_sphinx_theme'
html_static_path = []
