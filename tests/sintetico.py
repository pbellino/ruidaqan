"""
Generación de mediciones sintéticas con espectro conocido.

Se simulan dos cadenas de medición cuyas fluctuaciones normalizadas son

    x_i(t) = c(t) + w_i(t)

con
    c   : componente correlacionada, NPSD = A / (1 + (2 pi f / alfa)^2)
    w_i : ruido blanco independiente, NPSD = C

La señal AC de cada cadena es V_dc * x_i(t), de modo que con una función de
transferencia plana (H = 1) los espectros normalizados que calcula ruidaqan
deben reproducir A, C y alfa. La potencia esperada surge de A con las
constantes del reactor:

    P = 2 E_f D (1 - beta) L / (beta^2 A)

Los archivos se escriben con el mismo formato que usa la adquisición
(HDF5) y que usaba el FERCIN-3 (.RUI).
"""

import pickle
from pathlib import Path

import numpy as np
import tables as tb

# Parámetros por defecto de las mediciones sintéticas
BW = 200.0
FS = 2 * BW
N_PUNTOS = 512
HISTORIAS = 100
ALFA = 1 / 0.008340          # 1/Lambda_red del RA-3 [1/s]
P_W = 1000.0                 # potencia simulada [W]
A_SOBRE_C = 3.0              # cociente amplitud / meseta de la NPSD
GANANCIA_AC = 100.0          # define el nombre de la transferencia TR1200A*
V_DC = 2.0                   # tensión DC sin offset ni fondo [V]
OFFSET_DC = 0.1              # offset de la cadena DC [V]
SENSIBILIDAD = 1e-6          # [A/V]
COEF_AC = (0.0, 2e-7)        # conversión int16 -> V de la AC
COEF_DC = (0.0, 1e-4)        # conversión int16 -> V de la DC


def constante_potencia(reactor):
    """K tal que P = K / A, con las mismas constantes que usa ruidaqan."""
    return (2 * reactor.ENERGIA_FISION * reactor.FACTOR_DIVEN
            * (1 - reactor.BETA_EFECTIVO) * reactor.FACTOR_FORMA_L
            / reactor.BETA_EFECTIVO**2)


def fluctuaciones(A, C, alfa, fs, n, n_det=2, seed=0):
    """
    Fluctuaciones normalizadas x_i(t) = c(t) + w_i(t) con NPSD unilateral
    exactamente lorentziana (síntesis en el dominio de la frecuencia).
    """
    rng = np.random.default_rng(seed)
    f = np.fft.rfftfreq(n, 1 / fs)
    s_c = A / (1 + (2 * np.pi * f / alfa) ** 2)

    def proceso(S):
        # rfft de ruido blanco de varianza 1 tiene PSD unilateral 2/fs
        X = np.fft.rfft(rng.standard_normal(n))
        return np.fft.irfft(X * np.sqrt(S * fs / 2), n)

    c = proceso(s_c)
    return [c + proceso(C * np.ones_like(f)) for _ in range(n_det)]


def _a_int(volts, coef):
    """Inversa de la conversión lineal int -> V."""
    return np.round((volts - coef[0]) / coef[1]).astype(np.int16)


def escribe_hdf5(path, reactor, potencia=P_W, alfa=ALFA, n_puntos=N_PUNTOS,
                 historias=HISTORIAS, seed=0, nombre_reactor="TEST"):
    """
    Escribe una medición sintética de dos cadenas con CIp adquirida.

    Returns
    -------
        dict con los valores verdaderos (A, C, alfa, P)
    """
    A = constante_potencia(reactor) / potencia
    C = A / A_SOBRE_C
    n = n_puntos * historias
    xs = fluctuaciones(A, C, alfa, FS, n, n_det=2, seed=seed)
    rng = np.random.default_rng(seed + 1)

    with tb.open_file(str(path), mode="w") as h5:
        for i, x in enumerate(xs):
            g = h5.create_group("/", f"Cadena_{i + 1}")
            g._v_attrs.Offset = OFFSET_DC
            g._v_attrs.AC_gains = GANANCIA_AC
            g._v_attrs.Sensibilidad = SENSIBILIDAD
            g._v_attrs.Fondo = np.array([0.0, 0.0])
            ac = h5.create_earray(g, "AC", obj=_a_int(V_DC * x, COEF_AC))
            ac.attrs.Coeficientes = np.asarray(COEF_AC)
            ac.attrs.Rango = np.array([-1.0, 1.0])
            ac.attrs.Canal = f"Dev1/ai{3 * i}"
            ac.attrs.Nombre = f"AC{i + 1}"
            dc_v = V_DC + OFFSET_DC + 1e-3 * rng.standard_normal(n)
            dc = h5.create_earray(g, "DC", obj=_a_int(dc_v, COEF_DC))
            dc.attrs.Coeficientes = np.asarray(COEF_DC)
            dc.attrs.Rango = np.array([-5.0, 5.0])
            dc.attrs.Canal = f"Dev1/ai{3 * i + 1}"
            dc.attrs.Nombre = f"DC{i + 1}"

        g = h5.create_group("/", "Cadena_Ip")
        g._v_attrs.Fondo = np.array([0.0, 0.0])
        g._v_attrs.Offset = 0.0
        g._v_attrs.Sensibilidad = SENSIBILIDAD
        ip_v = 1.5 + 1e-3 * rng.standard_normal(n)
        dc = h5.create_earray(g, "DC", obj=_a_int(ip_v, COEF_DC))
        dc.attrs.Coeficientes = np.asarray(COEF_DC)
        dc.attrs.Rango = np.array([-5.0, 5.0])
        dc.attrs.Canal = "Dev1/ai6"
        dc.attrs.Nombre = "Ip"

        a = h5.root._v_attrs
        a.Fecha, a.Hora = "08-11-2026", "12:00:00"
        a.Reactor, a.Nucleo, a.Serie = nombre_reactor, " ", 1
        a.N_detectores, a.CIp_adquirido = 2, True
        a.Comentario, a.Comentario_medicion = "sintético", "sintético"
        a.Nivel, a.Medicion = 1, 1
        a.BW, a.N_puntos, a.Historias = BW, n_puntos, historias
        a.Resolucion_DAC = 16
    return {"A": A, "C": C, "alfa": alfa, "P": potencia}


# Coeficientes int -> V propios de la medición .RUI sintética (rango 1 V).
# Son distintos de los genéricos de la NI USB-6353 a propósito, para poder
# detectar cuál de los dos se usó.
COEF_RUI = {1.0: [0.0, 2e-6, 0.0, 0.0]}


def escribe_rui(path, reactor, potencia=P_W, alfa=ALFA, n_puntos=N_PUNTOS,
                historias=HISTORIAS, seed=0, con_coeficientes=True):
    """
    Escribe una medición sintética en formato .RUI (dos detectores, 16 bits)
    y, opcionalmente, el archivo de coeficientes <Sxx>-coeficientes_int_to_volt.pkl
    """
    path = Path(path)
    A = constante_potencia(reactor) / potencia
    C = A / A_SOBRE_C
    n = n_puntos * historias
    xs = fluctuaciones(A, C, alfa, FS, n, n_det=2, seed=seed)
    Z = 1 / SENSIBILIDAD
    pendiente = COEF_RUI[1.0][1]

    ac = np.empty(2 * n, dtype=int)
    for i, x in enumerate(xs):
        ac[i::2] = np.round(V_DC * x / pendiente).astype(int) + 2**15

    lineas = ['"08-11-2026"', '"12:00:00"', f"{2 * n:.1f}",
              f"  {1 / FS:.14f}  {1.5e-6:.14f}  {1e-9:.14f}", "2", "0.0",
              "1", "1"]
    for i in range(2):
        lineas += [f'"Cadena {i + 1}"',
                   f"  {V_DC:.14f}  {1e-3:.14f}  {0.0:.14f}  {0.0:.14f}",
                   f"     {Z:.2f}     {Z * 0.01:.2f}",
                   f"     {GANANCIA_AC:.2f}    {GANANCIA_AC * 0.01:.2f}"]
    np.savetxt(path, ac, fmt="%i", header="\n".join(lineas), comments="")

    if con_coeficientes:
        serie = path.name.split("-")[0]
        with open(path.parent / f"{serie}-coeficientes_int_to_volt.pkl", "wb") as f:
            pickle.dump(COEF_RUI, f)
    return {"A": A, "C": C, "alfa": alfa, "P": potencia}


def escribe_transferencia_plana(carpeta, n_fft=N_PUNTOS, fs=FS, bw=BW,
                                ganancia=GANANCIA_AC, n_puntos=None):
    """
    Escribe TR{K/100}{BW}A{1,2}.PSD con H = 1 (mismo formato que TRA.EXE).
    n_puntos permite escribir una transferencia más corta que el espectro.
    """
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    f = np.fft.rfftfreq(n_fft, 1 / fs)
    if n_puntos is not None:
        f = f[:n_puntos]
    # Columnas: f, Re(CPSD), Im(CPSD), APSD1 [dB], APSD2 [dB]
    # Con APSD1 = APSD2 = 1 (0 dB) y CPSD = 1 resulta H = 1
    datos = np.column_stack([f, np.ones_like(f), np.zeros_like(f),
                             np.zeros_like(f), np.zeros_like(f)])
    encabezado = "\n".join(12 * ['"Transf"'])
    for k in (1, 2):
        nombre = f"TR{ganancia / 100:.0f}{bw:.0f}A{k}.PSD"
        np.savetxt(carpeta / nombre, datos, header=encabezado, comments="")
    return carpeta
