#!/usr/bin/env python3
"""
Lectura del archivo de corrientes de fondo (SXXX-FONDOS) al iniciar una
medición. No necesita archivos de medición ni la placa.
"""

import numpy as np
import pytest

from ruidaqan.gui.data_io import (FondoIncompatible, fondo_para_medicion,
                                  read_background, write_background)


def _escribe(tmp_path, filas):
    p = tmp_path / "S001-FONDOS"
    write_background(str(p), [f[0] for f in filas], [f[1] for f in filas])
    return str(p)


def test_una_fila_da_dos_dimensiones(tmp_path):
    p = _escribe(tmp_path, [(1e-9, 1e-11)])
    assert read_background(p).shape == (1, 2)


@pytest.mark.parametrize("n_det, filas, esperado_ip", [
    (1, [(1e-9, 1e-11)], [0.0, 0.0]),                          # 1 det, sin CIp
    (1, [(1e-9, 1e-11), (2e-9, 2e-11)], [2e-9, 2e-11]),        # 1 det, con CIp
    (2, [(1e-9, 1e-11), (3e-9, 3e-11)], [0.0, 0.0]),           # 2 det, sin CIp
    (2, [(1e-9, 1e-11), (3e-9, 3e-11), (2e-9, 2e-11)], [2e-9, 2e-11]),
])
def test_fondo_compatible(tmp_path, n_det, filas, esperado_ip):
    fondo = fondo_para_medicion(_escribe(tmp_path, filas), n_det)
    assert fondo.shape == (n_det + 1, 2)
    np.testing.assert_allclose(fondo[:n_det], np.asarray(filas)[:n_det])
    np.testing.assert_allclose(fondo[-1], esperado_ip)


def test_sin_archivo_da_fondo_nulo(tmp_path):
    fondo = fondo_para_medicion(str(tmp_path / "S009-FONDOS"), 2)
    assert fondo.shape == (3, 2) and not fondo.any()


@pytest.mark.parametrize("n_det, n_filas", [(2, 1), (1, 3), (2, 4)])
def test_fondo_incompatible(tmp_path, n_det, n_filas):
    """
    Antes: con 2 detectores y un archivo de una fila, ValueError de numpy al
    abrir la ventana de adquisición (cierre del programa).
    """
    p = _escribe(tmp_path, n_filas * [(1e-9, 1e-11)])
    with pytest.raises(FondoIncompatible, match=f"{n_filas} fila"):
        fondo_para_medicion(p, n_det)


def test_archivo_vacio_es_incompatible(tmp_path):
    p = tmp_path / "S001-FONDOS"
    p.write_text("")
    with pytest.warns(UserWarning):
        with pytest.raises(FondoIncompatible, match="0 fila"):
            fondo_para_medicion(str(p), 2)
