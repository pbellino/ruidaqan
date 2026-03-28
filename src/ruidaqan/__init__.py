__version__ = "0.0.5"
__commit__ = "766a36aa5f15a454e34c3e6d8721781e2cb461e0"

import os

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
# v0.0.5

if os.name == "nt":
    os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"
