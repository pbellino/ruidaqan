#! /usr/bin/env python3
"""Punto de entrada para la ventana de resultados."""
import os
import sys

if sys.platform != "win32":
    os.environ["RUIDAQAN_DEBUG_MODE"] = "True"

from PyQt6.QtWidgets import QApplication
from ruidaqan.gui.resultados_window import ShowSpectrumFittedValues

def main():
    app = QApplication(sys.argv)
    win = ShowSpectrumFittedValues()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
