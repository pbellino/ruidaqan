#! /usr/bin/env python3
"""Punto de entrada para la ventana de procesamiento."""
import os
import sys

if sys.platform != "win32":
    os.environ["RUIDAQAN_DEBUG_MODE"] = "True"

from PyQt6.QtWidgets import QApplication
from ruidaqan.gui.procesamiento_window import FitWindow

def main():
    app = QApplication(sys.argv)
    win = FitWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
