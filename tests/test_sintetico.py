#!/usr/bin/env python3
"""
Tests con mediciones sintéticas de espectro conocido (ver sintetico.py).

No necesitan archivos de medición reales, así que corren en el CI. Se usa
una función de transferencia plana (H = 1), de modo que el procesamiento
debe recuperar los parámetros simulados.

Las tolerancias se fijaron a partir de un Monte Carlo de 300 realizaciones
con los mismos parámetros: dispersión relativa de ~5 % en la potencia
(NCPSD) y de ~5-7 % en alfa. Se usan márgenes de ~4 sigma para que los
tests no fallen por azar con otra semilla.
"""

import types
import warnings

import numpy as np
import pytest
import sintetico as s
from uncertainties import unumpy

from ruidaqan.constants import RA3
from ruidaqan.script import HDF5FileProcessing, RUIFileProcessing
from ruidaqan.script.data_fercin3_io import segmentos_equivalentes
from ruidaqan.script.fit_models import ajuste_apsd, ajuste_lineal, model_apsd

INTERVALOS = 2 * [(2.3, 178.9)] + [(2.3, 93)]


@pytest.fixture(scope="module")
def carpeta(tmp_path_factory):
    # El guion en el nombre de la carpeta reproduce el caso '/.../RA-3/...'
    c = tmp_path_factory.mktemp("RA-3")
    s.escribe_transferencia_plana(c / "transf" / "PLANA")
    return c


@pytest.fixture(scope="module")
def medicion_hdf5(carpeta):
    path = carpeta / "S001-N1-1.h5"
    verdad = s.escribe_hdf5(path, RA3, seed=1)
    return str(path), verdad


@pytest.fixture(scope="module")
def medicion_rui(carpeta):
    path = carpeta / "S31-N3-1.RUI"
    verdad = s.escribe_rui(path, RA3, seed=2)
    return str(path), verdad


def procesa(obj, carpeta, n_overlap=0, **kw):
    obj.TRANSFERS_FOLDER = str(carpeta / "transf")
    obj.get_spectrums(s.N_PUNTOS, n_overlap)
    obj.get_normalized_spectrums("PLANA")
    obj.fit_spectrums(INTERVALOS, **kw)
    obj.calcula_parametros_cineticos(RA3)
    return obj.parametros_cineticos


def relativo(valor, verdad):
    return unumpy.nominal_values(valor).item() / verdad - 1


# ---------------------------------------------------------------------------
# Cadena completa
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("ponderado", [False, True])
def test_hdf5_recupera_parametros(medicion_hdf5, carpeta, ponderado):
    path, verdad = medicion_hdf5
    par = procesa(HDF5FileProcessing(path), carpeta, ponderado=ponderado)
    for k in range(3):
        assert abs(relativo(par[k]["potencia"], verdad["P"])) < 0.20
        assert abs(relativo(par[k]["alfa"], verdad["alfa"])) < 0.25
    # Meseta: f_q = C I / 2, con I = (V_DC) * sensibilidad
    corriente = s.V_DC * s.SENSIBILIDAD
    for k in range(2):
        assert abs(relativo(par[k]["fq"], verdad["C"] * corriente / 2)) < 0.05


def test_rui_recupera_parametros_con_guion_en_carpeta(medicion_rui, carpeta):
    """
    Con el código anterior el archivo de coeficientes no se encontraba
    (la carpeta tiene un guion) y la potencia daba ~260 veces menor.
    """
    path, verdad = medicion_rui
    assert "-" in str(carpeta.name)
    with warnings.catch_warnings():
        warnings.simplefilter("error")      # no debe usar los genéricos
        obj = RUIFileProcessing(path)
        par = procesa(obj, carpeta)
    assert abs(relativo(par[2]["potencia"], verdad["P"])) < 0.20


def test_rui_sin_coeficientes_avisa(tmp_path):
    path = tmp_path / "S40-N1-1.RUI"
    s.escribe_rui(path, RA3, historias=4, con_coeficientes=False)
    obj = RUIFileProcessing(str(path))
    with pytest.warns(UserWarning, match="coeficientes"):
        obj.get_temporal_signals()


@pytest.mark.parametrize("archivo, esperado", [
    ("S31-N3-1.RUI", "S31-coeficientes_int_to_volt.pkl"),
    ("datos/S31-N3-1.RUI", "datos/S31-coeficientes_int_to_volt.pkl"),
    ("/med/RA-3/S31-N3-1.RUI", "/med/RA-3/S31-coeficientes_int_to_volt.pkl"),
])
def test_ruta_archivo_coeficientes(archivo, esperado):
    falso = types.SimpleNamespace(file_name=archivo)
    obtenido = RUIFileProcessing.coeficientes_file(falso)
    assert obtenido.replace("\\", "/") == esperado


def test_transferencia_mas_corta_que_espectro(medicion_hdf5, tmp_path):
    path, verdad = medicion_hdf5
    s.escribe_transferencia_plana(tmp_path / "CORTA", n_puntos=200)
    obj = HDF5FileProcessing(path)
    obj.TRANSFERS_FOLDER = str(tmp_path)
    obj.get_spectrums(s.N_PUNTOS, 0)
    with pytest.warns(UserWarning, match="200 puntos"):
        obj.get_normalized_spectrums("CORTA")
    assert len(obj.f) == 200
    assert all(len(x) == 200 for x in obj.norm_spectrums)
    assert all(len(x) == 200 for x in obj.spectrums)
    # Se puede ajustar con un intervalo que quede dentro del rango recortado
    obj.fit_spectrums(3 * [(2.3, 150)])
    obj.calcula_parametros_cineticos(RA3)
    assert abs(relativo(obj.parametros_cineticos[2]["potencia"],
                        verdad["P"])) < 0.20


# ---------------------------------------------------------------------------
# Incerteza por lotes
# ---------------------------------------------------------------------------
def test_incerteza_por_lotes(medicion_hdf5, carpeta):
    path, verdad = medicion_hdf5
    obj = HDF5FileProcessing(path)
    procesa(obj, carpeta)
    antes_norm = [np.copy(x) for x in obj.norm_spectrums]
    antes_P = obj.parametros_cineticos[2]["potencia"].n

    u = obj.incerteza_por_lotes(RA3, "PLANA", INTERVALOS, n_lotes=10)

    assert len(u) == 3
    # El Monte Carlo da ~5 % para la potencia con la NCPSD
    assert 0.02 < u[2]["potencia"] / verdad["P"] < 0.12
    assert len(u[2]["potencia_lotes"]) == 10
    # Los resultados previos quedan intactos
    assert obj.parametros_cineticos[2]["potencia"].n == antes_P
    assert len(obj.f) == len(antes_norm[0])
    for a, b in zip(antes_norm, obj.norm_spectrums):
        assert np.array_equal(a, b)


def test_segmentos_equivalentes():
    # Sin solapamiento: K segmentos independientes
    assert segmentos_equivalentes(51200, 512, 0) == pytest.approx(100)
    # Hann con 50 %: rho(1) = 1/6 (Percival & Walden, tabla 292)
    K = (51200 - 256) // 256
    esperado = K / (1 + 2 * (1 - 1 / K) / 36)
    assert segmentos_equivalentes(51200, 512, 256) == pytest.approx(esperado)


# ---------------------------------------------------------------------------
# fit_models
# ---------------------------------------------------------------------------
def test_ajuste_apsd_con_incertezas():
    """Antes fallaba con NameError ('daata')."""
    rng = np.random.default_rng(0)
    f = np.linspace(2, 180, 200)
    verdad = dict(alfa=120.0, amplitud=1e-9, constante=3e-10)
    S = model_apsd(f, **verdad)
    n = 100
    datos = S * rng.chisquare(2 * n, size=f.size) / (2 * n)
    res = ajuste_apsd(f, datos, std_psd=S / np.sqrt(n))
    assert res.params["alfa"].value == pytest.approx(120, rel=0.1)


def test_ajuste_lineal_sin_incertezas_escala_covarianza():
    rng = np.random.default_rng(0)
    x = np.linspace(1, 10, 20)
    y = 3.0 * x + 1.0 + 0.5 * rng.standard_normal(x.size)
    a, b, r2, cov, _ = ajuste_lineal(x, y, np.zeros_like(y))
    _, cov_ref = np.polyfit(x, y, 1, cov=True)
    assert a.s == pytest.approx(np.sqrt(cov_ref[0, 0]))
    # Con cov='unscaled' habría dado la incerteza para sigma = 1, el doble
    # de la real en este caso (los residuos tienen sigma = 0.5)
    _, cov_unscaled = np.polyfit(x, y, 1, cov="unscaled")
    assert a.s < 0.7 * np.sqrt(cov_unscaled[0, 0])
