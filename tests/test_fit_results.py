#!/usr/bin/env python3
"""Tests de lectura y análisis de resultados de ajuste (FitResults)."""

from ruidaqan.script import FitResults


def test_fit_results_carga(fit_results_file):
    fit_results = FitResults(fit_results_file)
    assert fit_results is not None


def test_fit_results_p_vs_I(fit_results_file):
    fit_results = FitResults(fit_results_file)
    fit_results.fit_p_vs_I()
    assert fit_results.fited_p_vs_I is not None
    assert len(fit_results.fited_p_vs_I) > 0


def test_fit_results_Ip_vs_I(fit_results_file):
    fit_results = FitResults(fit_results_file)
    fit_results.fit_Ip_vs_I(plot=False)


def test_fit_results_promedio(fit_results_file):
    fit_results = FitResults(fit_results_file)
    fit_results.average_parameters(plot=False)
