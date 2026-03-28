"""
Configuración de la aplicación.

Reemplaza a config.py. La carpeta de trabajo del usuario se guarda en:
  - Linux:   ~/.local/share/ruidaqan/config.json
  - Windows: C:\\Users\\usuario\\AppData\\Local\\ruidaqan\\config.json
"""

import json
from pathlib import Path
from platformdirs import user_data_dir
from PyQt6.QtWidgets import QFileDialog, QMessageBox

# ── Configuración interna ─────────────────────────────────────────────────────

_CONFIG_FILE = Path(user_data_dir("ruidaqan")) / "config.json"

# Constante de compatibilidad con el resto del código
RESET_DEFAULT_PARAMS = False


def _load():
    """Carga la configuración guardada."""
    try:
        return json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(data):
    """Guarda la configuración."""
    _CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ── API pública ───────────────────────────────────────────────────────────────

def get_data_folder(parent=None):
    """
    Retorna la carpeta de trabajo del usuario.

    Si no hay una carpeta guardada o no existe, abre un diálogo
    para que el usuario la elija.

    Parameters
    ----------
    parent : QWidget, optional
        Ventana padre para el diálogo.

    Returns
    -------
    Path
        Carpeta de trabajo seleccionada.
    """
    cfg = _load()
    folder = cfg.get("data_folder")
    if folder and Path(folder).exists():
        return Path(folder)
    return ask_data_folder(parent)


def ask_data_folder(parent=None):
    """
    Abre un diálogo para que el usuario elija la carpeta de trabajo
    y la guarda en la configuración.

    Parameters
    ----------
    parent : QWidget, optional
        Ventana padre para el diálogo.

    Returns
    -------
    Path
        Carpeta de trabajo seleccionada.
    """

    folder = QFileDialog.getExistingDirectory(
        parent,
        "Seleccionar carpeta de trabajo",
        str(Path.home()),
    )
    if folder:
        folder = Path(folder)
        cfg = _load()
        cfg["data_folder"] = str(folder)
        _save(cfg)
        return folder

    # El usuario canceló — crear carpeta por defecto
    folder = Path.home() / "Datos"
    folder.mkdir(parents=True, exist_ok=True)
    cfg = _load()
    cfg["data_folder"] = str(folder)
    _save(cfg)
    QMessageBox.information(
        parent,
        "Carpeta de trabajo",
        f"No se seleccionó ninguna carpeta.\n"
        f"Se utilizará la carpeta por defecto:\n{folder}",
    )
    return folder

