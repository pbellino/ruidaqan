#!/usr/bin/env python3
"""Tests de lectura y procesamiento de archivos RUI (.RUI del FERCIN-3)."""

import pytest
from ruidaqan.script import RUIFileProcessing
from ruidaqan.constants import RA1 as REACTOR


def test_rui_lectura_metadata(rui_file):
    rui = RUIFileProcessing(rui_file)
    assert rui.rango is not None
    assert rui.ADC_resolution is not None
    assert rui.I is not None


def test_rui_señales_temporales(rui_file):
    rui = RUIFileProcessing(rui_file)
    rui.get_temporal_signals()


def test_rui_espectros(rui_file):
    rui = RUIFileProcessing(rui_file)
    spect, fs = rui.get_spectrums(512, 0)
    assert spect is not None
    assert fs is not None


def test_rui_espectros_normalizados(rui_file):
    rui = RUIFileProcessing(rui_file)
    rui.get_spectrums(512, 0)
    norm_spect, fs = rui.get_normalized_spectrums(
        "RA1", freqs_to_remove=[50, 100, 150]
    )
    assert norm_spect is not None


def test_rui_ajuste_espectros(rui_file):
    rui = RUIFileProcessing(rui_file)
    rui.get_spectrums(512, 0)
    rui.get_normalized_spectrums("RA1", freqs_to_remove=[50, 100, 150])

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
