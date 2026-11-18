#!/usr/bin/env python3
"""
Tests de las correcciones menores de la revisión: saturación negativa, nombre
del .RUI, transferencias faltantes y scripts que no deben ejecutarse al
importarse.
"""

import importlib
import sys
from types import SimpleNamespace

import numpy as np
import pytest

import sintetico as s
from ruidaqan.constants import RA3
from ruidaqan.gui.data_io import nombre_archivo_rui
from ruidaqan.script import HDF5FileProcessing


# ----------------------------------------------------------------- .RUI
@pytest.mark.parametrize("h5, rui", [
    ("/datos/S010-N1-1.h5", "/datos/S10-N1-1.RUI"),
    # Carpeta con "S0" y ".h5" en el nombre: antes se modificaba la ruta
    ("/datos/S0-viejos.h5/S010-N2-3.h5", "/datos/S0-viejos.h5/S10-N2-3.RUI"),
    ("S100-N1-1.h5", "S100-N1-1.RUI"),
])
def test_nombre_archivo_rui(h5, rui):
    assert nombre_archivo_rui(h5).replace("\\", "/") == rui


# ------------------------------------------------------------ saturación
def _validador(n_canales=3, tipo_med="Ruido"):
    """ Lo mínimo de ProgresoMedicion para los métodos de saturación """
    emitidas = []
    v = SimpleNamespace(
        SATURATION_BIT=2**15 - 1, SATURATION_AC_ANTIALIAS=4.0,
        saturation_range=np.zeros(n_canales, dtype=int),
        saturation_ac_filt=np.zeros(n_canales, dtype=int),
        max_range_sat=5, max_ac_sat=5, tipo_med=tipo_med, dc_idx=[1],
        data_saturation=SimpleNamespace(emit=lambda *a: emitidas.append(a)))
    return v, emitidas


def test_saturacion_de_rango_negativa():
    from ruidaqan.gui.procesado_gui import ProgresoMedicion as ValidateData
    v, emitidas = _validador()
    datos = np.zeros((3, 100), dtype=np.int16)
    datos[0, :10] = 2**15 - 1          # satura positivo
    datos[2, :10] = -2**15             # satura negativo (antes no se veía)
    ValidateData.check_saturation_ranges(v, datos)
    np.testing.assert_array_equal(v.saturation_range, [10, 0, 10])
    assert emitidas == [("Rango", [0, 2])]


def test_saturacion_filtro_antialias_negativa():
    from ruidaqan.gui.procesado_gui import ProgresoMedicion as ValidateData
    v, emitidas = _validador(n_canales=2)
    ac = np.zeros((2, 100))
    ac[0, :10] = 4.5
    ac[1, :10] = -4.5
    ValidateData.check_saturation_antialiasing(v, ac)
    np.testing.assert_array_equal(v.saturation_ac_filt, [10, 10])


# ---------------------------------------------------------- transferencias
def test_transferencia_faltante_da_mensaje_claro(tmp_path):
    path = tmp_path / "S001-N1-1.h5"
    s.escribe_hdf5(path, RA3, seed=3)
    obj = HDF5FileProcessing(str(path))
    obj.TRANSFERS_FOLDER = str(tmp_path / "transf")
    with pytest.raises(FileNotFoundError, match="RA4") as e:
        obj.get_normalized_spectrums("RA4", s.N_PUNTOS, 0)
    assert "TR" in str(e.value) and ".PSD" in str(e.value)


# ------------------------------------------------------------- scripts
def test_modifica_corrientes_fondo_no_modifica_al_importar(tmp_path,
                                                          monkeypatch):
    """
    Antes el script abría y modificaba S001-N1-1.h5 del directorio actual
    al importarse (por ejemplo, al generar la documentación del código)
    """
    monkeypatch.chdir(tmp_path)
    nombre = "ruidaqan.script.modifica_corrientes_fondo"
    sys.modules.pop(nombre, None)
    modulo = importlib.import_module(nombre)
    assert callable(modulo.modifica_corrientes_fondo)
    assert not (tmp_path / "S001-N1-1.h5").exists()
