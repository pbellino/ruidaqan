# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html
#import os
#import sys
#sys.path.insert(0, os.path.abspath('../src/ruidaqan'))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'RuiDAQAn'
copyright = '2023, División Física Experimental de Reactores'
author = 'División Física Experimental de Reactores'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

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
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'pydata_sphinx_theme'
html_static_path = ['_static']

# -- Mocking de dependencias pesadas -----------------------------------------
import unittest.mock

MOCK_MODULES = [
    'PyQt5', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets',
    'PyQt5.QtWebEngineWidgets', 'numpy', 'pandas', 'matplotlib',
    'matplotlib.pyplot', 'pyqtgraph'
]
for mod_name in MOCK_MODULES:
    sys.modules[mod_name] = unittest.mock.Mock()
