#! /usr/bin/env python3

"""GUI for the neutron noise measurement program"""

import sys
from PyQt6.QtWidgets import QApplication, QMainWindow
from ruidaqan.gui.ruidaq_main import MainWindow
from ruidaqan.gui.procesamiento_window import FitWindow
from ruidaqan.gui.resultados_window import ShowSpectrumFittedValues

def main() -> None:
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
            win = FitWindow()
        elif sys.argv[1] in ["resultados", 'r']:
            win = ShowSpectrumFittedValues()
        else:
            print(msg)
            raise ValueError("Argumento erróneo")
    win.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
