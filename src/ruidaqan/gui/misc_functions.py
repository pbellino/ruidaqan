import numpy as np
from numpy.polynomial.polynomial import polyval
from scipy import signal


def calculate_spectrum_gui(data, fs=1.0):
    """
    Estimación espectral para la graficación
    """
    f, psd  = signal.periodogram(data, fs, detrend=False)
    return f, psd


def int_to_volt(incoming_data, coeficientes):
    """
    Convierte datos de I16 a voltaje con coeficientes de calibración

    incoming_data: list of numpy array (int16)
    coeficientes: list of numpy array (floats)

    Ambas entradas deben ser lista con igual tamaño
    """
    # Array donde se guardarán los voltajes
    data_volts = np.ones_like(incoming_data, dtype=float)
    for k, (inc_data, coef) in enumerate(zip(incoming_data, coeficientes)):
        data_volts[k, :] = polyval(inc_data, coef)
    return data_volts


def calculate_mean_value(data):
    return np.mean(data)


def weighted_average(data, weights):
    """
    ave(data) = sum(data*weights) / sum(weights)

    var(data) = var(data) * mean(weights**2) / mean(weights)**2 / n
    std(data) = sqrt(var(data))
    """
    if len(data) != len(weights):
        raise ValueError("Los datos y los pesos no tienen el mismo tamaño")

    mean_data = np.sum(data * weights) / np.sum(weights)
    if len(data) > 1:
        _var = np.var(data, ddof=1) * np.mean(weights**2) / np.mean(weights)**2 / len(data)
    else:
        _var = 1 / weights[0]**2
    std_data = np.sqrt(_var)
    return mean_data, std_data


if __name__ == "__main__":
    a = np.asarray([12, 11, 10])
    w = np.asarray([1, 2, 1.5])

    mean, std = weighted_average(a, w)
    print(f"{mean} +/- {std}")
    print(np.std(a, ddof=1) / np.sqrt(len(a)))


