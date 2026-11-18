#! /usr/bin/env python3

"""GUI for the neutron noise measurement program"""

import sys
from PyQt6.QtWidgets import QApplication, QMainWindow
from ruidaqan.gui.ruidaq_main import MainWindow
from ruidaqan.gui.procesamiento_window import FitWindow
from ruidaqan.gui.resultados_window import ShowSpectrumFittedValues
from ruidaqan.gui.appconfig import get_carpeta_lectura, aplica_escala

def main() -> None:
    # Escala de la interfaz elegida en el menú (antes de crear la aplicación)
    aplica_escala()
    app = QApplication(sys.argv)
    msg ="\n\nLos argumentos pueden ser: "
    msg += "[a]dquisición, [p]rocesamiento, [r]esultados]"
    msg += 4*'\n'
    if len(sys.argv) == 1:
        print(msg)
        raise ValueError("Faltó ingresar el argumento")
    else:
        if sys.argv[1] in ["adquisición", 'a']:
            win = MainWindow()
        elif sys.argv[1] in ["procesamiento", 'p']:
            # Abiertas solas, arrancan en la última carpeta desde la que se
            # abrió un archivo (no cambia la carpeta de la adquisición)
            win = FitWindow(folder=get_carpeta_lectura())
        elif sys.argv[1] in ["resultados", 'r']:
            win = ShowSpectrumFittedValues(folder=str(get_carpeta_lectura()))
        else:
            print(msg)
            raise ValueError("Argumento erróneo")
    win.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
