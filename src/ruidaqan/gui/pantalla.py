"""
Tamaño y posición de las ventanas según la pantalla disponible.

Las ventanas tenían tamaños fijos pensados para monitores de escritorio. En una
notebook (por ejemplo, 1920x1080 al 150 %, que son 1280x720 píxeles lógicos,
menos la barra de tareas) quedaban más grandes que la pantalla y se perdían
los botones de abajo. Estas funciones respetan el tamaño pedido cuando entra
y lo achican cuando no.
"""

import os

from PyQt6.QtWidgets import QApplication, QInputDialog, QMessageBox

from .appconfig import get_escala, set_escala, ESCALA_MIN, ESCALA_MAX

# Lugar para la barra de título, que no forma parte de la geometría de la
# ventana (setGeometry y resize se refieren al área interior)
MARGEN_TITULO = 40


def _area_disponible(ventana):
    """ Área de la pantalla sin la barra de tareas (None si no hay pantalla) """
    pantalla = ventana.screen() or QApplication.primaryScreen()
    return pantalla.availableGeometry() if pantalla is not None else None


def tamano_en_pantalla(ventana, ancho, alto):
    """ Tamaño pedido, acotado al área disponible de la pantalla """
    disp = _area_disponible(ventana)
    if disp is None:
        return ancho, alto
    return (min(ancho, disp.width()),
            min(alto, disp.height() - MARGEN_TITULO))


def ajusta_tamano(ventana, ancho, alto):
    """ resize(ancho, alto) sin superar el área disponible de la pantalla """
    ventana.resize(*tamano_en_pantalla(ventana, ancho, alto))


def ubica_en_pantalla(ventana, x, y, ancho, alto):
    """
    setGeometry(x, y, ancho, alto) con x, y relativos al área disponible,
    achicando la ventana si no entra y corriéndola para que quede completa
    dentro de la pantalla (con lugar para la barra de título arriba)
    """
    disp = _area_disponible(ventana)
    if disp is None:
        ventana.setGeometry(x, y, ancho, alto)
        return
    ancho, alto = tamano_en_pantalla(ventana, ancho, alto)
    x = min(max(x, 0), disp.width() - ancho)
    y = min(max(y, MARGEN_TITULO // 4 * 3), disp.height() - alto)
    ventana.setGeometry(disp.x() + x, disp.y() + y, ancho, alto)


def elige_escala(parent=None):
    """
    Diálogo para elegir la escala de la interfaz. Se guarda en la
    configuración y se aplica la próxima vez que se abra el programa.
    """
    dlg = QInputDialog(parent)
    dlg.setWindowTitle("Escala de la interfaz")
    dlg.setLabelText(
        "Factor de escala de ventanas, letras y botones\n"
        "(menor que 1 achica; útil en notebooks):")
    dlg.setInputMode(QInputDialog.InputMode.DoubleInput)
    dlg.setDoubleRange(ESCALA_MIN, ESCALA_MAX)
    dlg.setDoubleDecimals(2)
    dlg.setDoubleStep(0.05)
    dlg.setDoubleValue(get_escala())
    if not dlg.exec():
        return
    set_escala(dlg.doubleValue())
    texto = (f"Escala {dlg.doubleValue():.2f} guardada. Se aplica la próxima "
             "vez que se abra el programa.")
    if os.environ.get("QT_SCALE_FACTOR"):
        texto += ("\n\nAtención: la variable de entorno QT_SCALE_FACTOR "
                  f"(= {os.environ['QT_SCALE_FACTOR']}) está definida y tiene "
                  "prioridad sobre este valor.")
    QMessageBox.information(parent, "Escala de la interfaz", texto)
