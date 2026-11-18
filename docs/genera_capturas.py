#!/usr/bin/env python3
"""
Genera las capturas de la ayuda de las ventanas de procesamiento y de
resultados, sin pantalla ni placa de adquisición:

    make capturas
    (o: python docs/genera_capturas.py [carpeta_de_salida])

Se procesa con la GUI real una serie sintética (RA-3, 4 niveles x 2
mediciones, tests/sintetico.py) con una función transferencia plana, y las
corrientes proporcionales a la potencia para que los ajustes de calibración
tengan sentido. Por defecto las imágenes se escriben en docs/manual/images.

No modifica la configuración del usuario: usa una carpeta temporal y su propio
config.json.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "tests"))
sys.path.insert(0, str(RAIZ / "src"))

# Pantalla virtual (sin ventanas en el escritorio) de 1600 x 1000
_tmp = Path(tempfile.mkdtemp(prefix="ruidaqan_capturas_"))
_pantalla = _tmp / "pantalla.json"
_pantalla.write_text(json.dumps({
    "synchronousWindowSystemEvents": True, "windowFrameMargins": False,
    "screens": [{"name": "captura", "x": 0, "y": 0, "width": 1600,
                 "height": 1000, "logicalDpi": 96, "logicalBaseDpi": 96,
                 "dpr": 1}]}))
os.environ.setdefault("QT_QPA_PLATFORM", f"offscreen:configfile={_pantalla}")

import tables as tb                                          # noqa: E402
import PyQt6.QtWebEngineWidgets                              # noqa: E402,F401
from PyQt6.QtWidgets import (QApplication, QFileDialog,      # noqa: E402
                             QMessageBox)

app = QApplication(sys.argv)
app.setStyle("Fusion")

import sintetico as s                                        # noqa: E402
from ruidaqan.constants import RA3                           # noqa: E402
from ruidaqan.gui import appconfig                           # noqa: E402
from ruidaqan.script import data_fercin3_io as dio           # noqa: E402

datos = _tmp / "datos"
datos.mkdir()
appconfig._CONFIG_FILE = _tmp / "config.json"
appconfig._CONFIG_FILE.write_text(json.dumps({"data_folder": str(datos)}))

from ruidaqan.gui.procesamiento_window import FitWindow      # noqa: E402

salida = Path(sys.argv[1]) if len(sys.argv) > 1 \
    else RAIZ / "docs" / "manual" / "images"
salida.mkdir(parents=True, exist_ok=True)

# Función transferencia plana (H = 1): los parámetros ajustados reproducen
# los simulados
transf = _tmp / "transf"
s.escribe_transferencia_plana(transf / "RA3")
_init = dio._ProcesamientoEspectral.__init__


def _init_plano(self, *a, **k):
    _init(self, *a, **k)
    self.TRANSFERS_FOLDER = str(transf)


dio._ProcesamientoEspectral.__init__ = _init_plano
QMessageBox.information = staticmethod(lambda *a, **k: 0)

archivos = []
for nivel, potencia in enumerate((500, 1000, 2000, 4000), start=1):
    for med in (1, 2):
        p = datos / f"S012-N{nivel}-{med}.h5"
        s.escribe_hdf5(p, RA3, potencia=potencia, seed=10 * nivel + med,
                       nombre_reactor="RA-3")
        with tb.open_file(str(p), "a") as f:
            # Corriente proporcional a la potencia (los espectros normalizados
            # no dependen de la sensibilidad)
            for g in ("Cadena_1", "Cadena_2", "Cadena_Ip"):
                f.get_node("/" + g)._v_attrs.Sensibilidad = \
                    s.SENSIBILIDAD * potencia / 1000
            a = f.root._v_attrs
            a.Serie, a.Nivel, a.Medicion, a.Nucleo = 12, nivel, med, " "
        archivos.append(str(p))

ventana = FitWindow()
for ruta in archivos:
    QFileDialog.getOpenFileName = staticmethod(
        lambda *a, r=ruta, **k: (r, ""))
    ventana.get_time_file()
    ventana.graba_resultados()

ventana.show()
ventana.showNormal()
ventana.resize(1250, 900)
app.processEvents()
ventana.grab().save(str(salida / "pantalla_procesamiento.png"))

res = ventana.prev_win
res.showNormal()
res.resize(1500, 820)
res.tabs_view.setCurrentIndex(0)
app.processEvents()
res.grab().save(str(salida / "pantalla_resultados.png"))

res.dsp_pot.setValue(3000.0)
res.tabs_view.setCurrentIndex(1)
res.tabs_corrientes.setCurrentIndex(2)
app.processEvents()
res.grab().save(str(salida / "pantalla_resultados_ajustes.png"))

print(f"Capturas en {salida}")
print(f"  fp = {res.lbl_fp.text()} W/A (simulado {1000 / 1.5e-6:.3g})")
print(f"  alfa = {res.lbl_alfa.text()} 1/s (simulado {s.ALFA:.1f})")
