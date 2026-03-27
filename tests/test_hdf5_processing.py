#!/usr/bin/env python3
"""Tests de lectura y procesamiento de archivos HDF5 (.h5)."""

import pytest
from ruidaqan.script import HDF5FileProcessing
from ruidaqan.constants import RA3 as REACTOR


def test_hdf5_lectura_metadata(hdf5_file):
    rui = HDF5FileProcessing(hdf5_file)
    assert rui.date is not None
    assert rui.hour is not None
    assert rui.resolucion_DAC is not None


def test_hdf5_corrientes(hdf5_file):
    rui = HDF5FileProcessing(hdf5_file)
    assert rui.I is not None
    assert rui.DC_volts is not None


def test_hdf5_espectros(hdf5_file):
    rui = HDF5FileProcessing(hdf5_file)
    spect, fs = rui.get_spectrums(512, 0)
    assert spect is not None
    assert fs is not None


def test_hdf5_espectros_normalizados(hdf5_file):
    rui = HDF5FileProcessing(hdf5_file)
    rui.get_spectrums(512, 0)
    norm_spect, fs = rui.get_normalized_spectrums(
        "RA3", freqs_to_remove=[50, 100, 150]
    )
    assert norm_spect is not None


def test_hdf5_ajuste_espectros(hdf5_file):
    rui = HDF5FileProcessing(hdf5_file)
    rui.get_spectrums(512, 0)
    rui.get_normalized_spectrums("RA3", freqs_to_remove=[50, 100, 150])

    bw = round(rui.BW)
    if bw == 200:
        intervalos = 2 * [(2.3, 178.9)] + [(2.3, 93)]
    elif bw == 40:
        intervalos = 3 * [(2.8, 35.8)]
    else:
        pytest.skip(f"BW={bw} no tiene intervalos definidos en el test")

    rui.fit_spectrums(intervalos, plot=False)
    rui.calcula_parametros_cineticos(REACTOR)

    assert rui.parametros_cineticos is not None
    assert len(rui.parametros_cineticos) > 0
