#! /usr/bin/env python3


import numpy as np
from lmfit import Minimizer, Parameters, report_fit
import matplotlib.pyplot as plt
import seaborn as sns
import uncertainties
from uncertainties import ufloat
import os
sns.set()


def calcula_parametros_cineticos(result, reactor, **kwargs):
    """
    TODO
    """

    # Se necesita para calcular el fq
    corriente = kwargs.get("corriente", None)

    # Valores estimados
    params_val = [result.params[s].value for s in result.var_names]

    # Nombre de las variables ajustadas
    _names = result.var_names
    # Asocio con sus incertezas
    if "constante" in _names :
        if "covar" in dir(result):
            alfa, amplitud, constante = uncertainties.correlated_values(params_val,
                                          result.covar, tags=result.var_names)
        else:
            alfa, amplitud, constante = params_val
            print("No se pudo estimar la matríz de covaarianza del ajuste")
    else:
        if "covar" in dir(result):
            alfa, amplitud = uncertainties.correlated_values(params_val,
                                          result.covar, tags=result.var_names)
        else:
            alfa, amplitud = params_val
            print("No se pudo estimar la matríz de covaarianza del ajuste")
        constante = None

    # Constantes cinéticas
    DIVEN = reactor.FACTOR_DIVEN
    BETA = reactor.BETA_EFECTIVO
    FORMA = reactor.FACTOR_FORMA_L
    EFISION = reactor.ENERGIA_FISION
    BENNETT = reactor.FACTOR_BENNETT

    # Cálculo del fq y eficiencia (sólo para APSD's)
    if constante is not None:
        fq = constante * corriente / 2
        efi_over_beta2 = amplitud * BENNETT / (1 - BETA) / FORMA \
                        / DIVEN / constante
    else:
        fq = None
        efi_over_beta2 = None

    # Cálculo de la potencia
    potencia = 2 * EFISION * DIVEN * (1 - BETA) * FORMA / BETA**2 / amplitud

    # Salida
    parametros = {"alfa": alfa,
                  "potencia": potencia,
                  "fq": fq,
                  "efi_over_beta2": efi_over_beta2,
                  }

    return parametros


def read_PSD_file(file_name):
    """
    Función para leer archivos .PSD producidos por el programa FERCIN5T

    Parameters
    ----------
        file_name : string
            Nombre del archivo con extensión PSD

    Returns
    -------
        dicc : dictionary
            dicc["FECHA"]
            dicc["HORA"]
            dicc["BW"] Ancho de banda de la adquisición (40Hz ó 200Hz)
            dicc["DT"] Diferencia de tiempo entre pedido y adquirido (s)
            dicc["Ip"] Corriente de la cadena CIp [A]
            dicc["IpE"] Incerteza en Ip [A]
            dicc["NDET"] Cantidad de cadenas utilizadas (1 ó 2)

            - Parámetros de la cadena 1
            dicc["V1"] Voltaje medio de cadena 1 [V]
            dicc["V1E"] Incerteza en V1 [V]
            dicc["I1F"] Corriente de fondo de I1 [A]
            dicc["I1FE"] Incerteza en I1F [A]
            dicc["Z1"] Inversa sensibilidad de cadena 1 [V/A]
            dicc["Z1E"] Incerteza en Z1 [V/A]
            dicc["K1"] Ganancia AC cadena 1
            dicc["K1E"] Incerteza en K1
            dicc["COM1"] Comentario sobre cadea 1
            - Parámetros de la cadena 2
            (en caso de existir, de lo contrario no se definen las claves)
            dicc["V2"] Voltaje medio de cadena 2 [V]
            dicc["V2E"] Incerteza en V2 [V]
            dicc["I2F"] Corriente de fondo de I2 [A]
            dicc["I2FE"] Incerteza en I2F [A]
            dicc["Z2"] Inversa sensibilidad de cadena 2 [V/A]
            dicc["Z2E"] Incerteza en Z2 [V/A]
            dicc["K2"] Ganancia AC cadena 2
            dicc["K2E"] Incerteza en K2
            dicc["COM2"] Comentario sobre cadea 2
            - Son todos numpy array's:
            dicc["FREQ"] Frecuencia [Hz]
            dicc["RECPSD"] Parte real de la CPSD [ver]
            dicc["IMCPSD"] Parte imaginaria de la CPSD [ver]
            dicc["APSD1"] APSD de 1 [dB]
            dicc["APSD2"] APSD de 2 [dB]

            En caso de no utilizar la cadena dos se obtiene
            dicc["RECPSD"] = dicc["IMCPSD"] = dicc["APSD2] = 0

    """


    dicc = {}
    with open(file_name, 'r') as f:
        # Fecha
        dicc["FECHA"] = f.readline().rstrip(' \n')

        # Hora
        dicc["HORA"] = f.readline().rstrip(' \n')

        # Ancho de banda, Dif. tiempos, I_p, Incerteza I_p
        _line = [float(item) for item in f.readline().split()]
        dicc["BW"], dicc["DT"], dicc["Ip"], dicc["IpE"] = _line
        dicc["NDET"] = int(f.readline().rstrip('\n'))

        # ---- Lectura canal 1
        # Voltaje 1, Incerteza Voltaje 1, I_fondo 1, Incerteza I_fondo 1
        _line = [float(item) for item in f.readline().split()]
        dicc["V1"], dicc["V1E"], dicc["I1F"], dicc["I1FE"] = _line

        # Z1, Incerteza Z1
        _line = [float(item) for item in f.readline().split()]
        dicc["Z1"], dicc["Z1E"] = _line

        # Ganancia 1, Incerteza Ganancia 1
        _line = [float(item) for item in f.readline().split()]
        dicc["K1"], dicc["K1E"] = _line

        # Comentario cadena 1
        dicc["COM1"] = f.readline().rstrip('\n')

        # Encabezado si hay una sola cadena
        SKIP_HEADER = 8
        if dicc["NDET"] == 2:
            # ---- Lectura canal 2
            # Voltaje 1, Incerteza Voltaje 1, I_fondo 1, Incerteza I_fondo 2
            _line = [float(item) for item in f.readline().split()]
            dicc["V2"], dicc["V2E"], dicc["I2F"], dicc["I2FE"] = _line

            # Z1, Incerteza Z1
            _line = [float(item) for item in f.readline().split()]
            dicc["Z2"], dicc["Z2E"] = _line

            # Ganancia 1, Incerteza Ganancia 1
            _line = [float(item) for item in f.readline().split()]
            dicc["K2"], dicc["K2E"] = _line

            # Comentario cadena 1
            dicc["COM2"] = f.readline().rstrip('\n')


            # Encabezado si hay dos cadenas
            SKIP_HEADER = 12

        # Lectura de los datos
        # Frecuencia [Hz]   Re(CPSD)    Im(CPSD)    APSD1[dB]    APSD2[dB]
        _data = np.loadtxt(file_name, skiprows=SKIP_HEADER)
        # Frecuencia [Hz]
        dicc["FREQ"] = _data[:, 0]
        # Re(CPSD)
        dicc["RECPSD"] = _data[:, 1]
        # Im(CPSD)
        dicc["IMCPSD"] = _data[:, 2]
        # APSD1 [dB]
        dicc["APSD1"] = _data[:, 3]
        # APSD2 [dB]
        dicc["APSD2"] = _data[:, 4]

        # Si sólo hay una cadena: Re(CPSD)=Im(CPSD)=APSD2=0's

    return dicc


def V2I_PSD(PSD_dic):
    """
    Función para convertir el voltaje leido de un .PSD a corriente

    Parameters
    ----------
        PSD_dic : dictionary
            Diccionario obtenido con la función 'read_PSD_file'

    Returns
    -------
        I1, I2 : float
            Valor de la corriente. Si sólo se utiliza una cámara, sólo I1.

    Convierte el voltaje (medio) leído del archivo .PSD a correinte con el
    factor inversa de la sensibilidad (Z). Finalmente le resta la corriente de
    fondo.

    TODO: Si esto se va a usar seriamente, agregar propagación de incerrtezas
    """

    I1 = PSD_dic['V1'] / PSD_dic['Z1'] - PSD_dic['I1F']
    if PSD_dic['NDET'] == 2:
        I2 = PSD_dic['V2'] / PSD_dic['Z2'] - PSD_dic['I2F']
        return [I1, I2]
    else:
        return [I1]


def dB2V(data):
    " Función para pasar de dB a Voltaje (revisar) "
    return 10**(data / 10)


def model_apsd(freq, alfa, amplitud, constante):
    return amplitud / ( 1 + (2*np.pi*freq/alfa)**2) + constante


def model_cpsd(freq, alfa, amplitud):
    return amplitud / ( 1 + (2*np.pi*freq/alfa)**2)


def _plot_fit(freq, psd,  result):

    best_fit = psd + result.residual

    fig, (ax0, ax1) = plt.subplots(2, sharex=True,
                        gridspec_kw={'height_ratios': [3,1]},)

    ax0.errorbar(freq, psd, fmt='k.', elinewidth=2,
                 label='Measurement')
    ax0.plot(freq, best_fit, 'r', zorder=3, label='fit')
    ax0.set_ylabel(r'PSD [1/Hz]')

    ax1.plot(freq, result.residual, 'k.')
    ax1.set_xlabel('f [Hz]')
    ax1.set_ylabel(r'Residuals [1/Hz]')
    fig.subplots_adjust(hspace=0.1)

    return ax0


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
        return (model - data) / sigma

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
    report_fit(result)

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
    report_fit(result)

    # _plot_fit(freq, psd, result)

    return result


def remove_utility_freq(frequency, spectrum, freqs_to_remove=[50, 100, 150]):
    """
    Removes the utility frequencies from the spectrum

    Values of 'spectrum' at those freqs (+/- 1Hz) are replaced with those
    of its neighbours (Angel's approach).


    Parameters
    ----------
        frequency : numpy array
            Vector with frequencies
        spectrum : numpy array
            Vector with the spectrum (should be same size of frequency)
        freqs_to_remove : double or array
            Frequency/ies to be removed

    Returns
    -------
        new_spectrum : numpy array
            Spectrum without the freqs_to_remove

    """

    # Force list
    if not isinstance(freqs_to_remove, list):
        freqs_to_remove = [freqs_to_remove]

    new_spectrum = np.copy(spectrum)

    for freqs in freqs_to_remove:
        indx_to_remove = (frequency > freqs-1) & (frequency < freqs + 1)
        # Closest value to (freqs - 1Hz)
        value_to_assign = new_spectrum[frequency <= freqs-1][-1]
        new_spectrum[indx_to_remove] = value_to_assign
        # print("Aviso: se quitó la frecuencia {} Hz".format(freqs))

    return new_spectrum


def get_transfer_function(file_name, freqs_to_remove=[50, 100, 150]):
    """
    Función para leer archivos .PSD con las funciones de transferencia
    producidas por el programa TRA.EXE.

    Se quitan también las frecuencias de línea.

    Parameters
    ----------
        file_name : string
            Nombre del archivo con extensión PSD de la función transferencia

    Returns
    -------
        H2_dB : numpy array
            Módulo cuadrado de la función transferencia. Expresado en dB
            10*log10(H2)
        ReH : numpy array
            Parte real de la función transferencia
        ImH : numpy array
            Parte imaginaria de la función transferencia

    """

    # TODO: Se podría poner en los comentarios de los archivos la
    # identificación del reactor (al menos). Para evitar confusiones.
    # Preguntar.

    SKIP_HEADER = 12
    # Lectura de los datos
    # Frecuencia [Hz]   Re(CPSD)    Im(CPSD)    APSD1[dB]    APSD2[dB]
    _data = np.loadtxt(file_name, skiprows=SKIP_HEADER)
    # Frecuencia [Hz]
    freq = _data[:, 0]
    # Re(CPSD)
    _ReCPSD = _data[:, 1]
    # Im(CPSD)
    _ImCPSD = _data[:, 2]
    # APSD1 [dB]
    _APSD1_dB = _data[:, 3]
    # APSD2 [dB]
    _APSD2_dB = _data[:, 4]

    # Módulo cuadrado de H(f)
    H2_dB = _APSD2_dB - _APSD1_dB
    # Parte real e imaginaria de H(f)
    _APSD1 = 10**(_APSD1_dB / 10)
    ReH = _ReCPSD / _APSD1
    ImH = _ImCPSD / _APSD1
    # Se quitan frecuencias de línea
    H2_dB = remove_utility_freq(freq, H2_dB, freqs_to_remove)
    ReH = remove_utility_freq(freq, ReH, freqs_to_remove)
    ImH = remove_utility_freq(freq, ImH, freqs_to_remove)

    return H2_dB, ReH, ImH


def obtain_normalized_spectrum(PSD_dic, get_spectrum="APSD1",
        freqs_to_remove=[50, 100, 150], reactor_name=None):
    """
    Función para normalizar los espectros (NPSD o CPSD)

    Se quitan tambén la frecuencia de línea y sus harmónicos

    TODO: corregir con función transferencia

    Parameters
    ----------
        PSD_dic : dictionary
            Diccionario obtenido con la función 'read_PSD_file'

        get_spectrum : string ("APSD1", "APSD2" ó "CPSD")
            Nombre del espectro que se desee calcular

        freqs_to_remove : double or array
            Frequency/ies to be removed

        reactor_name : string (Optional)
            Nombre del reactor. Se asume que los archivos están en:
                "trs/reactor_name/"
            El nombre "trs" está hardcodeado
            Si no se especifica, se toma la carpeta como "trs/"

    Returns
    -------
        f : numpy array
            Fecuencias
        NPSD_tr :  numpy array
            Espectro normalizado y corregido con la función transferencia.
            sin frecuencia de línea. En caso de haber pedido "CPSD", devuelve
            la parte real.

    """

    # Sólo se aceptan tres opciones para calcular espectros
    if get_spectrum not in ["APSD1", "APSD2", "CPSD"]:
        _msg = "Error en <obtain_normalized_spectrum>\n"
        _msg += "El espectro pedido debe ser 'APSD1', 'APSD2' o 'CPSD'.\n"
        _msg += "Se introdujo '{}'".format(get_spectrum)
        raise ValueError(_msg)

    # Si sólo se midió con una CIC y se pide APSD2 ó CPSD
    if get_spectrum in ["APSD2", "CPSD"] and PSD_dic["NDET"]==1:
        _msg = "Error en <obtain_normalized_spectrum>\n"
        _msg += "El archvio .PSD sólo tiene datos de una cámara\n"
        _msg += "Se pidieron espectros que involucar a una segunda."
        raise ValueError(_msg)

    _tr_names = get_transfer_name(PSD_dic, get_spectrum, reactor_name)

    _last_let = get_spectrum[-1]
    if _last_let=="1" or _last_let=="2":
        i_det = _last_let
    else:
        i_det = "12" # (CPSD)

    if i_det == "1" or i_det == "2":
        f = PSD_dic.get("FREQ")
        K = PSD_dic.get("K" + i_det)
        V = PSD_dic.get("V" + i_det)
        IF = PSD_dic.get("I" + i_det + "F")
        Z = PSD_dic.get("Z" + i_det)
        APSD_dB = PSD_dic[get_spectrum]
        # Obtengo la función transferencia
        # Las frecuencias a filtrar de H(f) pueden no ser las mismas que 
        # las frecuencias que se quieran quitar durante la medición
        H2_dB, _, _ = get_transfer_function(_tr_names[0], [50, 100, 150])
        print("Se normalizó con {}".format(_tr_names[0]))
        # En algunos casos del RA1 no coinciden los tamaños entre APSD y
        # la función tansferencia
        len_s, len_h = len(APSD_dB), len(H2_dB)
        if len_s != len_h:
            _min = min(len_s, len_h)
            f = f[:_min]
            APSD_dB = APSD_dB[:_min]
            H2_dB = H2_dB[:_min]
            print(80*'!')
            msg = "Advertencia: el tamaño de la función transferencia\n"
            msg += "no coincide con el tamaño del espectro medido \n"
            msg += "Se toma el mínimo entre ambos: {}"
            print(msg.format(_min))
            print(80*'!')
        # Se hace la corrección
        APSD_dB_tr = APSD_dB - H2_dB

        # Trabajo sin dB
        # APSD = dB2V(APSD_dB)    # Sin usar la función transferencia
        APSD_tr = dB2V(APSD_dB_tr)
        # Normalización con valor medio
        # Resto el vaor de fondo al voltaje medio
        V_sf = V - IF * Z
        NAPSD_tr = APSD_tr / V_sf**2
        # Ganancia AC (K) para pasar a voltaje común
        # NAPSD = APSD / K**2 / V_sf**2   # Sin usar la función tranferencia

        # Quito frecuencias de línea
        NAPSD_tr = remove_utility_freq(f, NAPSD_tr, freqs_to_remove)
        return f, NAPSD_tr
    elif i_det == "12":
        f = PSD_dic.get("FREQ")
        K1 = PSD_dic.get("K1")
        K2 = PSD_dic.get("K2")
        V1 = PSD_dic.get("V1")
        V2 = PSD_dic.get("V2")
        I1F = PSD_dic.get("I1F")
        I2F = PSD_dic.get("I2F")
        Z1 = PSD_dic.get("Z1")
        Z2 = PSD_dic.get("Z2")

        APSD1_dB = PSD_dic["APSD1"]
        APSD2_dB = PSD_dic["APSD2"]
        ReCPSD = PSD_dic["RECPSD"]
        ImCPSD = PSD_dic["IMCPSD"]
        # Obtengo las funciones transferencia
        H2_dB_1, ReH_1, ImH_1 = get_transfer_function(_tr_names[0],
                                                      freqs_to_remove)
        H2_dB_2, ReH_2, ImH_2 = get_transfer_function(_tr_names[1],
                                                      freqs_to_remove)
        print("Se normalizó con {} y {}".format(*_tr_names))
        # Trabajo sin dB
        APSD1 = dB2V(APSD1_dB)
        APSD1 = dB2V(APSD1_dB)
        H2_1 = dB2V(H2_dB_1)
        H2_2 = dB2V(H2_dB_2)

        # Corrección de la CPSD por función transferencia
        _c1 = ReH_1 * ReH_2 + ImH_1 * ImH_2
        _c2 = ImH_1 * ReH_2 - ReH_1 * ImH_2
        ReCPSD_tr = (_c1 * ReCPSD - _c2 * ImCPSD) / (H2_1 * H2_2)
        ImCPSD_tr = (_c1 * ImCPSD + _c2 * ReCPSD) / (H2_1 * H2_2)

        # Normalizo con valor medio
        # Resto el fondo al voltaje medio
        V1_sf = V1 - I1F * Z1
        V2_sf = V2 - I2F * Z2
        ReNCPSD_tr = ReCPSD_tr / (V1_sf * V2_sf)
        ImNCPSD_tr = ImCPSD_tr / (V1_sf * V2_sf)

        # En caso de no corregir con la función transferencia
        # Ganancia AC (K) para pasar a voltaje común
        # ReCPSD = ReCPSD / (K1*K2) / (V1_sf*V2_sf)

        # Quito frecuencias de línea
        ReNCPSD_tr = remove_utility_freq(f, ReNCPSD_tr, freqs_to_remove)
        return f, ReNCPSD_tr


def get_transfer_name(PSD_dic, get_spectrum, reactor_name=None):
    """
    Function to get the name of the transfer funcition file

    The file name is coeded as:
            TR[1,2,4,6,8][40,200]A[1,2].PSD

    The first number is K/100
    The second number is BW
    The thirdnumber is de detection system id

    Parameters
    ----------
        PSD_dic : dictionary
            Diccionario obtenido con la función 'read_PSD_file'

        get_spectrum : string ("APSD1", "APSD2" ó "CPSD")
            Nombre del espectro que se desee calcular

        reactor_name : string (Optional)
            Nombre del reactor. Se asume que los archivos están en:
                "trs/reactor_name/"
            El nombre "trs" está hardcodeado
            Si no se especifica, se toma la carpeta como "trs/"
            TODO: definir la estructura luego.

    Returns
    -------
        path_file : touple
            Complete paths of the transfer function files
            One elmenent in case APSD, two if CPSD

    """

    # Folders with the transfer function files
    CURRENT_FOLDER = os.path.dirname(os.path.realpath(__file__))
    PARENT = os.path.dirname(CURRENT_FOLDER)
    FOLDER_NAME = os.path.join(PARENT, "transferencias")
    if reactor_name:
        sub_folder = reactor_name
    else:
        sub_folder = ""

    BW = PSD_dic["BW"]
    if get_spectrum[-1] in ["1", "2"]:
        system_id = get_spectrum[-1]
        K_over_100 = np.round(PSD_dic["K" + system_id] / 100)
        file_name = "TR{:.0f}{:.0f}A{}.PSD".format(K_over_100, BW, system_id)
        path_file = os.path.join(FOLDER_NAME, sub_folder, file_name)
        return path_file,
    else:
        K1_over_100 = np.round(PSD_dic["K1"] / 100)
        K2_over_100 = np.round(PSD_dic["K2"] / 100)
        file_name_1 = "TR{:.0f}{:.0f}A1.PSD".format(K1_over_100, BW)
        file_name_2 = "TR{:.0f}{:.0f}A2.PSD".format(K2_over_100, BW)
        path_file_1 = os.path.join(FOLDER_NAME, sub_folder, file_name_1)
        path_file_2 = os.path.join(FOLDER_NAME, sub_folder, file_name_2)
        return path_file_1, path_file_2


if __name__ == "__main__":
    import sys
    CURRENT_FOLDER = os.path.dirname(os.path.realpath(__file__))
    PARENT = os.path.dirname(CURRENT_FOLDER)
    sys.path.append(PARENT)
    from constantes.constantes_reactores import RA3 as REACTOR

    # Carpeta con los archivos .PSD
    folder = os.path.join(PARENT, "test_files")
    # Frecuencias de línea que se queiren quitar
    freqs_to_remove = [50, 100, 150]

    # Con una cámara
    # archivo = "S23-N1-1.PSD"   # RA1
    # archivo = "S23-N1-2.PSD"   # RA1
    # archivo = "S20-N2-2.PSD"   # RA1
    # Con dos cámaras
    archivo = "S98-N1-1.PSD"   # RA3
    #archivo = "S98-N1-2.PSD"   # RA3
    #archivo = "S98-N2-1.PSD"   # RA3

    path_archivo = os.path.join(folder, archivo)

    react_name = REACTOR.__name__

    # Lectura del archivo PSD
    dic_content = read_PSD_file(path_archivo)
    # Calcula corrientes medias
    Corrientes = V2I_PSD(dic_content)

    # Selección de lo que se quiere calcular
    if dic_content["NDET"] == 2:
        dos_det = True
        # list_espectros = ["APSD1", "APSD2"]
        list_espectros = ["APSD1", "APSD2", "CPSD"]
        # list_espectros = ["CPSD"]
    else:
        dos_det = False
        list_espectros = ["APSD1"]

    def _selec_int_ajuste(fre, psd, tipo, bw):
        " Selección del intervalo de ajuste"
        if bw == 200:
            f_min = 2.3
            f_max = 178.9
            if "CPSD" in tipo:
                f_max = 93.0
        else:
            f_min = 2.8
            f_max = 35.8
        ind = (fre>=f_min) & (fre<=f_max)
        return fre[ind], psd[ind], (f_min, f_max)

    # Ajuste de los datos
    for key, corr in zip(list_espectros, Corrientes + [None] ):
        f, NPSD = obtain_normalized_spectrum(dic_content, key, freqs_to_remove,
                                             react_name)
        # Modelo de ajustes
        if "APSD" in key:
            f_int, NPSD_int, f_lim = _selec_int_ajuste(f, NPSD, key,
                                                        dic_content["BW"])
            result = ajuste_apsd(f_int, NPSD_int)
        elif "CPSD" in key:
            f_int, NPSD_int, f_lim = _selec_int_ajuste(f, NPSD, key,
                                                        dic_content["BW"])
            result = ajuste_cpsd(f_int, NPSD_int)

        # Cálculo de parámetros cinéticos
        _extra = {"corriente": corr}
        params = calcula_parametros_cineticos(result, REACTOR, **_extra)

        print(80*'=')
        print("\t\t PARÁMETROS CALCULADOS CON EL ESPECTRO {}".format(key))
        print(80*'=')
        print("Archivo analizado: {} ({})".format(archivo, key))
        print("Constantes del reactor {}".format(REACTOR.__name__))
        print("Invervalo de ajuste [Hz]: [{}, {}]".format(*f_lim))
        print("alfa: {:.2f} 1/s".format(params["alfa"]))
        if params["fq"] is not None:
            print("fq: {:.4e} C".format(params['fq']))
        print("Potencia: {:.2f} W".format(params['potencia']))
        if params["efi_over_beta2"] is not None:
            print("efi/beta2: {:.2f}".format(params["efi_over_beta2"]))
        if corr is not None:
            print("Corriente media : {:.2e} A".format(corr))
        print(80*'=')

    plt.show()
