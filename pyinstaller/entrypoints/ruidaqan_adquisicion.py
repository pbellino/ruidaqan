#! /usr/bin/env python3
"""Punto de entrada para la ventana de adquisición."""
import os
import sys

if sys.platform != "win32":
    os.environ["RUIDAQAN_DEBUG_MODE"] = "True"

from PyQt6.QtWidgets import QApplication
from ruidaqan.gui.ruidaq_main import MainWindow
from ruidaqan.gui.appconfig import aplica_escala

def main():
    # Escala de la interfaz (antes de crear la aplicación)
    aplica_escala()
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
