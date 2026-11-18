#!/usr/bin/env python3
"""
Tests del análisis de la tabla de resultados (FitResults) con tablas
sintéticas de relación conocida:

    P = 5e8 * I1 = 4e8 * I2 = 6e8 * Ip,   fq1 = 2e-20 * nivel

Cubren los errores de emparejamiento por posición (filas borradas, archivos
no ordenados por nivel) y la llamada repetida a fit_Ip_vs_I.
"""

import numpy as np
import pytest
from uncertainties import ufloat, unumpy

from ruidaqan.script.data_fercin3_io import FitResults
from ruidaqan.gui.misc_functions import weighted_average as wa_misc


def tabla(niveles, mediciones=None, n_det=2, ruido=0.0, seed=1):
    """ Tabla de resultados (una fila por espectro) en el formato actual """
    rng = np.random.default_rng(seed)
    mediciones = mediciones or list(range(1, len(niveles) + 1))
    filas = []
    for nivel, med in zip(niveles, mediciones):
        P = 100.0 * nivel
        I1, I2, Ip = P / 5e8, P / 4e8, P / 6e8
        Pm = P * (1 + ruido * rng.standard_normal())
        comun = [nivel, med, 200]
        Ipu = ufloat(Ip, Ip * 0.01)
        filas.append(comun + ["NPSD1", Ipu, ufloat(I1, I1 * 0.01),
                              ufloat(120, 5), ufloat(Pm, 0.05 * P),
                              ufloat(2e-20 * nivel, 1e-21),
                              ufloat(3.0, 0.1), 0.5, "ajuste"])
        if n_det == 2:
            filas.append(comun + ["NPSD2", Ipu, ufloat(I2, I2 * 0.01),
                                  ufloat(121, 5), ufloat(Pm, 0.05 * P),
                                  ufloat(3e-20 * nivel, 1e-21),
                                  ufloat(3.1, 0.1), 0.5, "ajuste"])
            filas.append(comun + ["NCPSD", Ipu, None, ufloat(119, 4),
                                  ufloat(Pm, 0.04 * P), None, None, 0.5,
                                  "ajuste"])
    return np.asarray(filas, dtype=object)


def pendiente(fr, k):
    return fr.fited_p_vs_I[k][0].n


def test_fit_Ip_vs_I_se_puede_llamar_dos_veces():
    fr = FitResults(data=tabla([1, 2, 3]))
    fr.fit_Ip_vs_I(plot=False)
    fr.fit_Ip_vs_I(plot=False)
    # Ip = (5e8 / 6e8) * I1
    assert fr.fited_Ip_vs_I[0][0].n == pytest.approx(5 / 6, rel=1e-6)
    assert callable(fr.fit_Ip_vs_I)


def test_emparejamiento_con_filas_borradas():
    """
    Se borra la NCPSD de la medición del nivel 1 y la NPSD1 del nivel 3:
    los ajustes no deben emparejar corrientes y potencias de mediciones
    distintas (antes: IndexError o pares desfasados)
    """
    t = tabla([1, 2, 3, 4])
    t = np.delete(t, [2, 6], axis=0)
    fr = FitResults(data=t)
    fr.fit_p_vs_I(plot=False)
    assert pendiente(fr, 0) == pytest.approx(5e8, rel=1e-6)
    assert pendiente(fr, 1) == pytest.approx(4e8, rel=1e-6)
    assert pendiente(fr, 2) == pytest.approx(6e8, rel=1e-6)
    m = fr.mediciones
    assert np.isnan(m.loc[m["Nivel"] == 1, "Pc"].iloc[0].n)
    assert np.isnan(m.loc[m["Nivel"] == 3, "I1"].iloc[0].n)
    # La Ip de la medición sin NPSD1 se toma de otro espectro
    assert m.loc[m["Nivel"] == 3, "Ip"].iloc[0].n == pytest.approx(300 / 6e8)


def test_fq_emparejado_en_archivo_no_ordenado():
    """ Nivel 1 grabado después del 2: cada I1 debe ir con su fq1 """
    fr = FitResults(data=tabla([2, 2, 1, 1, 3, 3], [1, 2, 1, 2, 1, 2]))
    I1 = unumpy.nominal_values(fr.I_fq1.to_numpy())
    fq1 = unumpy.nominal_values(fr.fqs[0].to_numpy())
    np.testing.assert_allclose(I1 * 5e8 / 100, fq1 / 2e-20)


def test_potencia_media_por_nivel_para_alfa_y_efi():
    fr = FitResults(data=tabla([1, 1, 2], [1, 2, 1]))
    np.testing.assert_allclose(fr.P_nivel.to_numpy(dtype=float),
                               [100, 100, 200])
    np.testing.assert_allclose(fr.pote_bylevel.to_numpy(), [100, 200])


def test_un_detector():
    fr = FitResults(data=tabla([1, 2, 3], n_det=1))
    assert fr.n_det == 1
    fr.fit_p_vs_I(plot=False)
    fr.fit_Ip_vs_I(plot=False)
    fr.average_parameters(plot=False)
    assert pendiente(fr, 0) == pytest.approx(5e8, rel=1e-6)
    # Sin detector 2: no hay ajuste ni promedio
    assert fr.fited_p_vs_I[1] == [[]]
    assert np.isnan(fr.fqs_av[1][0])
    assert fr.alfa_prom == pytest.approx(120)


def test_un_solo_punto_no_ajusta():
    t = tabla([1, 2])
    t = np.delete(t, [5], axis=0)          # NCPSD del nivel 2
    fr = FitResults(data=t)
    fr.fit_p_vs_I(plot=False)
    assert all(f == [[]] for f in fr.fited_p_vs_I)


def test_tabla_vacia():
    fr = FitResults(data=np.empty((0, 12), dtype=object))
    fr.fit_p_vs_I(plot=False)
    fr.average_parameters(plot=False)
    assert np.isnan(fr.alfa_prom)


def test_promedios_ignoran_valores_faltantes():
    t = tabla([1, 2, 3])
    t = np.delete(t, [2], axis=0)          # NCPSD del nivel 1 (alfa)
    fr = FitResults(data=t)
    fr.average_parameters(plot=False)
    assert fr.alfa_prom == pytest.approx(119)


def test_weighted_average_un_solo_valor():
    """ Con un dato la incerteza es la del dato (antes daba sigma^2) """
    media, std = wa_misc(np.array([2e-6]), 1 / np.array([3e-8])**2)
    assert media == pytest.approx(2e-6)
    assert std == pytest.approx(3e-8)
