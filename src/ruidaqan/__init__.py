__version__ = "0.1.10"
__commit__ = ""

import os
import subprocess

# Constante para saber si se cargarán o no los drivers de NI
# Se lee como variable de entorno del sistema
debug_mode_str = os.getenv('RUIDAQAN_DEBUG_MODE', "False")

if debug_mode_str not in ["True", "False"]:
    msg = "La variable de entorno RUIDAQAN_DEBUG_MODE sólo puede ser "
    msg += f"True o False. El valor actual es {debug_mode_str}"
    raise ValueError(msg)

# Convierto de string a bool
DEBUG_MODE = eval(debug_mode_str)

# Se define esta variable de entorno porque en windows se encontró
# que no era posible mostrar la ventana de ayuda. Quedaba una ventana
# en blanco.
#
# TODO: verificar si sigue siendo válida en futuras versiones de los
# paquetes
# v0.1.10

if os.name == "nt":
    os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"


if not __commit__:
    try:
        __commit__ = subprocess.check_output(
            ['git', 'rev-parse', '--short', 'HEAD'],
            stderr=subprocess.DEVNULL
        ).decode('ascii').strip()
    except Exception:
        __commit__ = "desconocido"
