#!/usr/bin/env python3
"""
Tests del ajuste de las ventanas a la pantalla y de la escala de la interfaz
(sin abrir ventanas: se simulan la pantalla y la ventana).
"""

import json

import pytest
from PyQt6.QtCore import QRect

from ruidaqan.gui import appconfig, pantalla


class _Pantalla:
    def __init__(self, ancho, alto, x=0, y=0):
        self._g = QRect(x, y, ancho, alto)

    def availableGeometry(self):
        return self._g


class _Ventana:
    """ Lo mínimo de una ventana: pantalla, resize y setGeometry """
    def __init__(self, pantalla_):
        self._p = pantalla_
        self.geometria = None

    def screen(self):
        return self._p

    def resize(self, ancho, alto):
        self.geometria = (None, None, ancho, alto)

    def setGeometry(self, x, y, ancho, alto):
        self.geometria = (x, y, ancho, alto)


@pytest.mark.parametrize("pedido, esperado", [
    # Monitor grande: se respeta lo pedido
    ((10, 30, 1300, 690), (10, 30, 1300, 690)),
    # Notebook 1280x720: se achica y se corre para que entre completa
    ((10, 30, 1300, 690), (0, 30, 1280, 680)),
])
def test_ubica_en_pantalla(pedido, esperado):
    grande = esperado == pedido
    v = _Ventana(_Pantalla(1920, 1040) if grande else _Pantalla(1280, 720))
    pantalla.ubica_en_pantalla(v, *pedido)
    assert v.geometria == esperado


def test_ubica_respeta_el_origen_del_area_disponible():
    """ Barra de tareas arriba o a la izquierda: el área no empieza en 0 """
    v = _Ventana(_Pantalla(1240, 680, x=40, y=40))
    pantalla.ubica_en_pantalla(v, 360, 30, 350, 690)
    x, y, ancho, alto = v.geometria
    assert (ancho, alto) == (350, 640)
    assert x == 40 + 360 and y >= 40
    assert y + alto <= 40 + 680


def test_ajusta_tamano():
    v = _Ventana(_Pantalla(1280, 720))
    pantalla.ajusta_tamano(v, 500, 800)
    assert v.geometria[2:] == (500, 720 - pantalla.MARGEN_TITULO)
    pantalla.ajusta_tamano(v, 400, 400)
    assert v.geometria[2:] == (400, 400)


@pytest.fixture
def config(tmp_path, monkeypatch):
    archivo = tmp_path / "config.json"
    monkeypatch.setattr(appconfig, "_CONFIG_FILE", archivo)
    monkeypatch.delenv("QT_SCALE_FACTOR", raising=False)
    return archivo


def test_escala_por_defecto_no_cambia_nada(config):
    import os
    assert appconfig.get_escala() == 1.0
    appconfig.aplica_escala()
    assert "QT_SCALE_FACTOR" not in os.environ


def test_escala_guardada_se_aplica(config):
    import os
    appconfig.set_escala(0.8)
    assert json.loads(config.read_text())["escala"] == 0.8
    appconfig.aplica_escala()
    assert os.environ["QT_SCALE_FACTOR"] == "0.8"


def test_variable_de_entorno_tiene_prioridad(config, monkeypatch):
    import os
    appconfig.set_escala(0.8)
    monkeypatch.setenv("QT_SCALE_FACTOR", "1.25")
    appconfig.aplica_escala()
    assert os.environ["QT_SCALE_FACTOR"] == "1.25"


@pytest.mark.parametrize("valor", [5, 0.1, "abc", None])
def test_escala_invalida_se_ignora(config, valor):
    config.write_text(json.dumps({"escala": valor}))
    assert appconfig.get_escala() == 1.0
