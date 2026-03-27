#! /usr/bin/env pythn3

import numpy as np
from lmfit import Minimizer, Parameters, report_fit
from uncertainties import correlated_values


def ajuste_apsd(freq, psd, std_psd=None):
    """
    Ajuste no lineal de espectros (ver cuál)
    """

    def residual(params, freq, data=None, sigma=None):
        " TODO: pensar mejor los nombres "
        parvals = params.valuesdict()
        alfa = parvals['alfa']
        amplitud = parvals['amplitud']
        constante = parvals['constante']

        model = model_apsd(freq, alfa, amplitud, constante)

        if data is None:
            return model
        if sigma is None:
            return model - data
        return (model - daata) / sigma

    # Se definen los parámetros del ajuste
    params = Parameters()
    params.add('alfa', value=100, min=20, max=300)
    params.add('amplitud', value=np.mean(psd))
    params.add('constante', value=np.mean(psd))

    # Se define la minimización
    minner = Minimizer(residual, params, fcn_args=(freq,),
            fcn_kws={'data': psd, 'sigma': std_psd}
                       )

    result = minner.minimize(method='leastsq')
    #report_fit(result)

    # _plot_fit(freq, psd, result)

    return result


def ajuste_cpsd(freq, psd, std_psd=None):
    """
    Ajuste no lineal de espectros (ver cuál)

    TODO: Angel usa la coherencia como función de peso (sólo en la CPSD, no en
    la APSD). Ver si es necesario.
    """

    def residual(params, freq, data=None, sigma=None):
        " TODO: pensar mejor los nombres "
        parvals = params.valuesdict()
        alfa = parvals['alfa']
        amplitud = parvals['amplitud']

        model = model_cpsd(freq, alfa, amplitud)

        if data is None:
            return model
        if sigma is None:
            return model - data
        return (model - data) / sigma

    # Se definen los parámetros del ajuste
    params = Parameters()
    params.add('alfa', value=100)
    params.add('amplitud', value=np.mean(psd))

    # Se define la minimización
    minner = Minimizer(residual, params, fcn_args=(freq,),
            fcn_kws={'data': psd, 'sigma': std_psd}
                       )

    result = minner.minimize(method='leastsq')
    # report_fit(result)

    # _plot_fit(freq, psd, result)

    return result


def model_apsd(freq, alfa, amplitud, constante):
    return amplitud / ( 1 + (2*np.pi*freq/alfa)**2) + constante


def model_cpsd(freq, alfa, amplitud):
    return amplitud / ( 1 + (2*np.pi*freq/alfa)**2)


def rsquared(y_data, y_fit, y_sigma=None):
        """ Calcula el factur R^2 del ajuste lineal """
        if y_sigma is None:
            y_sigma = np.ones_like(y_data)
        # Factor de peso 1/sigma^2
        w = 1.0 / y_sigma**2
        # Normalizado
        w = w / np.sum(w)
        ss_res = np.sum(w * (y_data - y_fit)**2)
        ss_tot = np.sum(w * (y_data - np.average(y_data, weights=w))**2)
        return 1 - (ss_res / ss_tot)


def ajuste_lineal(x, y, y_sig, *args, **kargs):
    """
    Ajuste lineal de los datso
        y = a * x + b

    Devuelve los parámetros a y b en tipo ufloat, con  sus errores
    correlacionados a partir de la matriz de covarianza del ajuste
    """

    if any(y_sig==0):
        p, cov = np.polyfit(x, y, deg=1, cov='unscaled')
        # Mejor ajuste evaluado en x
        y_fit = np.polyval(p, x)
        # Valor r2 del ajuste
        r_squared = rsquared(y, y_fit)
    else:
        p, cov = np.polyfit(x, y, deg=1, w=1/y_sig, cov='unscaled')
        # Mejor ajuste evaluado en x
        y_fit = np.polyval(p, x)
        # Valor r2 del ajuste
        r_squared = rsquared(y, y_fit, y_sig)
    # Convierto a tipo ufloat con errores correlacionados
    a, b = correlated_values(p, cov, tags=('a', 'b'))

    return a, b, r_squared, cov, y_fit


def weighted_average(data, weights):
    """
    ave(data) = sum(data*weights) / sum(weights)

    var(data) = var(data) * mean(weights**2) / mean(weights)**2 / n
    std(data) = sqrt(var(data))

    Se suele tomar weights = 1 / sigma**2
    """
    if len(data) != len(weights):
        raise ValueError("Los datos y los pesos no tienen el mismo tamaño")

    # Sólo se dan resultados válidos para arrays no vacios
    if len(data) > 0:
        mean_data = np.sum(data * weights) / np.sum(weights)
        if len(data) > 1:
            _var = np.var(data, ddof=1) * np.mean(weights**2) / np.mean(weights)**2 / len(data)
        elif len(data) == 1:
            _var = 1 / weights[0]
        else:
            _var = 0.0
        std_data = np.sqrt(_var)
        return mean_data, std_data
    else:
        return None, None


if __name__ == "__main__":

    I1, _, I1_s = np.loadtxt("I1-S21.EST", skiprows=6, delimiter=',',
            unpack=True)
    Ip, _, Ip_s = np.loadtxt("IP-S21.EST", skiprows=6, delimiter=',',
            unpack=True)
    pot, _, pot_s = np.loadtxt("POTE-S21.EST", skiprows=6, delimiter=',',
            unpack=True)

    a, b, r2, cov, _ = ajuste_lineal(Ip, pot, pot_s)

    print(a)
    print(b)
    print(r2)
