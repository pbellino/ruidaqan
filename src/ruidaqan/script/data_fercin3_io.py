#! /usr/bin/env python3

import pandas as pd
import numpy as np
from numpy.polynomial.polynomial import polyval
import tables as tb
import os
import sys
import pickle
from scipy import signal
from uncertainties import ufloat, unumpy, correlated_values
import matplotlib.pyplot as plt
import seaborn as sns
sns.set()
try:
    from .fit_models import (ajuste_apsd, ajuste_cpsd, ajuste_lineal,
                               weighted_average)
except ImportError:
    from fit_models import (ajuste_apsd, ajuste_cpsd, ajuste_lineal,
                               weighted_average)


class HDF5FileProcessing():
    """
    Procesamiento de los archivos en formato HDF5 generados en la adquisición
    del programa.

    Permite calcular los espectros y graficarlos.

    Parameters
    ----------
        file_name : str
            Nombre del archivo en formato hdf5

    """

    def __init__(self, file_name):
        self.file_name = file_name

        self._read_file(self.file_name)

        current = os.path.dirname(os.path.realpath(__file__))
        parent = os.path.dirname(current)
        self.TRANSFERS_FOLDER = os.path.join(parent, "transferencias")


    def _read_file(self, file_name):
        with tb.open_file(file_name, mode="r") as f:
            # ---- Atributos del archivo
            aa = f.root._v_attrs

            self.date = aa.Fecha
            self.hour = aa.Hora
            self.reactor = aa.Reactor
            self.nucleo = aa.Nucleo
            self.serie = aa.Serie
            self.n_det = aa.N_detectores
            self.cip = aa.CIp_adquirido
            self.comentaario = aa.Comentario
            self.nivel = aa.Nivel
            self.medicion = aa.Medicion
            self.comentario_medicion = aa.Comentario_medicion
            self.BW = aa.BW
            self.dt = 1 / (2 * self.BW)
            self.n_puntos = aa.N_puntos
            self.historias = aa.Historias
            self.resolucion_DAC = aa.Resolucion_DAC


            self.AC_volts, self.DC_volts = [], []
            self.AC_rangos, self.DC_rangos = [], []
            self.AC_nombres, self.DC_nombres = [], []
            self.DC_volt_avg_sf = []
            self.If, self.I = [], []
            self.sensibilidades, self.AC_gains, self.offsets = [], [], []
            for i in range(self.n_det):
                g = f.get_node(f"/Cadena_{i + 1}")

                # Uso una incerteza del 1% en las sensibilidades
                # Es la incerteza de la resistencia que usa el conversor
                # corriente-voltaje (ver manual K330)
                # TODO: la incerteza guardarla en el archivo
                sensibilidad = ufloat(g._v_attrs.Sensibilidad,
                                      g._v_attrs.Sensibilidad * 0.01)
                self.sensibilidades.append(sensibilidad)

                AC_gan = g._v_attrs.AC_gains
                # Pongo a mano una incerteza para la ganancia del 0.5%
                # (es la incerteza que se le asigna en el FERCIN5)
                # TODO: la incerteza guardarla en el archivo
                self.AC_gains.append(ufloat(AC_gan, AC_gan * 0.005))

                offset = g._v_attrs.Offset
                self.offsets.append(offset)
                fondo = ufloat(*g._v_attrs.Fondo)
                self.If.append(fondo)

                AC_int = g.AC.read()
                self.AC_volts.append(polyval(AC_int, g.AC.attrs.Coeficientes))
                self.AC_rangos.append(g.AC.attrs.Rango)
                self.AC_nombres.append(g.AC.attrs.Nombre)

                DC_int = g.DC.read()
                DC_volt = polyval(DC_int, g.DC.attrs.Coeficientes)
                self.DC_volts.append(DC_volt)
                self.DC_rangos.append(g.DC.attrs.Rango)
                self.DC_nombres.append(g.DC.attrs.Nombre)

                DC_avg = ufloat(np.mean(DC_volt), np.std(DC_volt))
                self.I.append((DC_avg - offset) * sensibilidad - fondo)

                # Voltaje DC promedio sin fondo
                DC_volt_m_sf = DC_avg - offset - fondo / sensibilidad
                self.DC_volt_avg_sf.append(DC_volt_m_sf)

            # Para CIp
            g = f.get_node("/Cadena_Ip")
            self.If.append(ufloat(*g._v_attrs.Fondo))
            if self.cip:
                sensibilidad = ufloat(g._v_attrs.Sensibilidad, 0.0)
                self.sensibilidades.append(sensibilidad)
                offset = g._v_attrs.Offset
                self.offsets.append(offset)

                DC_int = g.DC.read()
                DC_volt = polyval(DC_int, g.DC.attrs.Coeficientes)
                self.DC_volts.append(DC_volt)
                self.DC_rangos.append(g.DC.attrs.Rango)
                self.DC_nombres.append(g.DC.attrs.Nombre)

                DC_avg = ufloat(np.mean(DC_volt), np.std(DC_volt))
                # Recordar que no se resta fondo a Ip
                self.Ip = (DC_avg - offset)  * sensibilidad

                # Voltaje DC promedio (no se resta fondo para Ip)
                DC_volt_m_sf = DC_avg - offset
                # Por comodidad lo pongo en la lista que ya estaba usando
                # a pesar de que Ip tiene el fondo
                self.DC_volt_avg_sf.append(DC_volt_m_sf)
            else:
                # Se leen valores ingreados de forma manual
                Ip_DC_mag = g.DC_mag.read()
                Ip_DC_std = g.DC_std.read()
                # Se calcula promedio pesado
                mean_Ip, std_Ip = weighted_average(Ip_DC_mag, 1 / Ip_DC_std**2)
                self.Ip = ufloat(mean_Ip, std_Ip)


    def get_temporal_signals(self):
        """ Calcula las AC en voltaje. Convierte dependiendo ADC """
        # Calculo la corriente DC temporal
        # Esto sólo se usa para graficar, no se incluyen las incertezas
        # (ver que se usa .n para las sensibilidades)
        I_DC = []
        for i, dc in enumerate(self.DC_volts):
            I_DC.append((dc - self.offsets[i]) * self.sensibilidades[i].n)
        # Vector temporal
        time_vec = np.arange(0, len(self.AC_volts[0])) * self.dt
        return time_vec, self.AC_volts, I_DC


    def get_spectrums(self, N_fft=None, N_overlap=None):
        """
        Espectros sin normalizar ni corregidos con función transferencia

        Son los valores que se guardan en los archivos .PSD con fercin3/5

        Se estima el espectro con el estimador de Welch utilizando N_fft
        puntos y N_overlap puntos de solapamiento.

        Returns
        -------
            self.spectrums: lists of numpy arrays
                Lista con los espectros [APSD1, APSD2, CPSD]
            self.f: numpy array
                Vector con las frecuencias asociada a los espectros
        """
        if (N_fft is None) or (N_overlap is None):
            raise ValueError("Faltan especificar N_fft o N_overlap")

        self.N_fft = N_fft
        self.N_overlap = N_overlap

        spectrums = []
        for AC in self.AC_volts:
            # Estimación de las APSD
            f_spectrums, _spec = signal.welch(AC, fs=1/self.dt,
                                      noverlap=N_overlap, nperseg=N_fft)
            spectrums.append(_spec)
        if self.n_det == 2:
            # Estimación de la CPSD
            _, _spec = signal.csd(self.AC_volts[0], self.AC_volts[1], fs=1/self.dt,
                                  noverlap=N_overlap, nperseg=N_fft)
            spectrums.append(_spec)
        self.spectrums = spectrums
        # Se convierten
        self.f = np.asarray(f_spectrums)
        return self.spectrums, self.f


    def get_normalized_spectrums(self, reactor_name, N_fft=None,
                                N_overlap=None, freqs_to_remove=[50, 100, 150],
                                freqs_to_remove_tr=[50, 100, 150]):
        """
        Calcula los espectros normalizados con el método de Welch.

        Se les quita las frencuencia de línea y sus dos armónicos.
        Están corregidos por la función transferencia.

        Si no se especifica N_fft y N_overlap se usan los espectros estimados
        con .get_spectrum(). Si se especifican, se vuelven a calcular.

        Parameters
        ----------
            N_fft: int
                Puntos para calcular la FFT en cada bloque
            N_overlap: int
                Cantidad de puntos para el solapamiento de bloques
            reactor_name: string
                Identificación del reactor (para leer transferencias)
            freqs_to_remove: list of floats
                Frecuencias que serán eliminadas del espectro medido
            freqs_to_remove: list of floats
                Frecuencias que serán eliminadas de las transferencias

        Returns
        -------
            self.spectrums: listr of numpy arrays
                Lista con los espectros [NPSD1, NPSD1, NCPSD12]
                Los NPSD son reales, la NCPSD es compleja
            self.f: numpy array
                Frecuencias asociadas a los espectros
        """

        # Si no se calcularon los espectros previamente, se los calcula
        if not hasattr(self, 'spectrums'):
            self.get_spectrums(N_fft, N_overlap)
        else:
            # Si se especifican los valores
            if N_fft or N_overlap:
                self.get_spectrums(N_fft, N_overlap)
        # Nombres de las funciones transferencia que voy a leer
        _tr_names = self._get_transfer_name(reactor_name)

        norm_spec = []
        _trans = []
        for i, _tr_name in enumerate(_tr_names):
            # Lectura de las funciones transferencia
            try:
                H2_dB, ReH, ImH = self._get_transfer_function(_tr_name,
                                                freqs_to_remove_tr)
            except IOError:
                _tr_name = os.path.join('..', _tr_name)
                H2_dB, ReH, ImH = self._get_transfer_function(_tr_name,
                                                freqs_to_remove_tr)

            # Módulo cuadrado de la función transferencia
            H2 = 10**(H2_dB / 10)
            _trans.append([H2, ReH, ImH])
            print(f"Se lee la función transferencia de {_tr_name}")
            # Espectro APSD
            APSD = self.spectrums[i]
            # En algunos casos del RA1 no coinciden los tamaños entre APSD y
            # la función tansferencia
            len_s, len_h = len(APSD), len(H2)
            if len_s != len_h:
                _min = min(len_s, len_h)
                f = f[:_min]
                APSD = APSD[:_min]
                H2 = H2[:_min]
                print(80*'!')
                msg = "Advertencia: el tamaño de la función transferencia\n"
                msg += "no coincide con el tamaño del espectro medido \n"
                msg += "Se toma el mínimo entre ambos: {}"
                print(msg.format(_min))
                print(80*'!')
            # Corrección por función transferencia
            APSD_tr = APSD / H2
            # Normalizo 
            NAPSD_tr = APSD_tr / self.DC_volt_avg_sf[i]**2
            # Quito frecuencias de línea
            NAPSD_tr = self._remove_utility_freq(
                                    self.f, NAPSD_tr, freqs_to_remove)
            # Los espectros tienen incertezas debido a la propagación, pero las
            # descarto por ahora:
            NAPSD_tr = unumpy.nominal_values(NAPSD_tr)
            norm_spec.append(NAPSD_tr)
        if len(_tr_names) == 2:
            # --- Corrección para la CPSD
            # Espectros sin corregir
            APSD1 = self.spectrums[0]
            APSD2 = self.spectrums[1]
            ReCPSD = np.real(self.spectrums[2])
            ImCPSD = np.imag(self.spectrums[2])
            # Funciones transferencia leidas anteriormente
            H2_1, ReH_1, ImH_1 = _trans[0]
            H2_2, ReH_2, ImH_2 = _trans[1]
            # Corrección de la CPSD por función transferencia
            _c1 = ReH_1 * ReH_2 + ImH_1 * ImH_2
            _c2 = ImH_1 * ReH_2 - ReH_1 * ImH_2
            ReCPSD_tr = (_c1 * ReCPSD - _c2 * ImCPSD) / (H2_1 * H2_2)
            ImCPSD_tr = (_c1 * ImCPSD + _c2 * ReCPSD) / (H2_1 * H2_2)
            # Normalizo con valor medio
            fac_norm = (self.DC_volt_avg_sf[0] * self.DC_volt_avg_sf[1])
            ReNCPSD_tr = ReCPSD_tr / fac_norm
            ImNCPSD_tr = ImCPSD_tr / fac_norm
            # Quito frecuencias de línea
            ReNCPSD_tr = self._remove_utility_freq(self.f, ReNCPSD_tr,
                                                  freqs_to_remove)
            ImNCPSD_tr = self._remove_utility_freq(self.f, ImNCPSD_tr,
                                                  freqs_to_remove)
            # Los espectros tienen incertezas debido a la propagación, pero las
            # descarto por ahora:
            ReNCPSD_tr = unumpy.nominal_values(ReNCPSD_tr)
            ImNCPSD_tr = unumpy.nominal_values(ImNCPSD_tr)
            # Guardo el espectro complejo
            norm_spec.append(ReNCPSD_tr + 1j * ImNCPSD_tr)
        self.norm_spectrums = norm_spec
        return self.norm_spectrums, self.f


    def _get_transfer_name(self, reactor_name):
        """
        Get names of transfer functions
        """
        #FOLDER_NAME = "transferencias"
        if reactor_name:
            sub_folder = reactor_name
        else:
            sub_folder = ""

        path_file = []
        for i, K in enumerate(self.AC_gains):
            K_over_100 = np.round(K.n / 100)
            if i !=3:
                file_name = "TR{:.0f}{:.0f}A{}.PSD".format(
                            K_over_100, self.BW, i+1)
                path_file.append(os.path.join(self.TRANSFERS_FOLDER,
                                 sub_folder, file_name))
        return path_file


    def _get_transfer_function(self, file_name, freqs_to_remove=[50, 100, 150]):
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
        H2_dB = self._remove_utility_freq(freq, H2_dB, freqs_to_remove)
        ReH = self._remove_utility_freq(freq, ReH, freqs_to_remove)
        ImH = self._remove_utility_freq(freq, ImH, freqs_to_remove)
        return H2_dB, ReH, ImH


    def _remove_utility_freq(self, frequency, spectrum, freqs_to_remove):
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


    def plot_spectrums(self, normalizados=True, *args, **kargs):
        if normalizados:
            if self.norm_spectrums is None:
                raise NameError("Faltan estimar los espectros normalizados")
            _datas = self.norm_spectrums
            _labels = ["NPSD1", "NPSD2", "Re(NCPSD12)"]
            _units = "[1 / Hz]"
        else:
            if self.spectrums is None:
                raise NameError("Faltan estimar los espectros")
            _datas = self.spectrums
            _labels = ["PSD1", "PSD2", "Re(CPSD12)"]
            _units = "[V$^2$ / Hz]"

        figs, ax = plt.subplots(1, 1)

        for i, data in enumerate(_datas):
            if i == 2:
                data = np.real(data)
            ax.plot(self.f, data, '.-', label=_labels[i])
        ax.set_xlabel("Frecuencia [Hz]")
        ax.set_ylabel("Espectro " + _units)
        ax.legend()
        ax.set_title(f"Archivo leido: {self.file_name}")
        figs.tight_layout()

        plt.show()


    def fit_spectrums(self, intervals, **kargs):
        """
        Ajuste de los espectros

        intervals: list of tuples
            Lista con los límitesde los intervalos para el ajuste
            [(f_min, f_max), (f_min, f_max), ...]
            en el orden [NPSD1, NPSD2, CPSD12]
        kargs:
              plot: bool
                True si se quiere graficar. False por default
        """

        if self.norm_spectrums is None:
            raise NameError("Faltan estimar los espectros normalizados")

        plot = kargs.get('plot', False)
        _ttle = ["NPSD1", "NPSD2", "Re(NCPSD12)"]
        _ylab = [i + " [1 / Hz]" for i in _ttle]

        self.fit_results = []
        self.fitted_data = []
        for i, (spe, inter) in enumerate(zip(self.norm_spectrums, intervals)):
            ind = (self.f >= inter[0]) & (self.f <= inter[1])
            if i != 2:
                _dat = spe[ind]
                _res = ajuste_apsd(self.f[ind], _dat)
            else:
                _dat = np.real(spe[ind])
                _res = ajuste_cpsd(self.f[ind], _dat)
            self.fit_results.append(_res)
            self.fitted_data.append([self.f[ind], _dat])

            if plot:
                best_fit = _dat + _res.residual
                fig, (ax0, ax1) = plt.subplots(2, sharex=True,
                               gridspec_kw={'height_ratios': [3,1]},)
                ax0.errorbar(self.f, np.real(spe), fmt='k.', elinewidth=2,
                             label='Medición')
                ax0.plot(self.f[ind], best_fit, 'r', zorder=3, label='fit')
                ax0.set_ylabel(_ylab[i])

                ax1.plot(self.f[ind], _res.residual, 'k.')
                ax1.set_xlabel('f [Hz]')
                ax1.set_ylabel(r'Residuos [1/Hz]')
                ax0.set_title(f"Ajuste de {_ttle[i]}")
                fig.subplots_adjust(hspace=0.1)

        if plot: plt.show()


    def calcula_parametros_cineticos(self, reactor, **kwargs):
        """
        Calcula parámetros cinéticos en base al ajuste espectral

        Parameters
        ----------
            reactor: reactor class
                Clase importada del archivo "constantes_reactores.py"

        Returns
        -------
            self.parametros_cineticos: dic
                Diccionario con los parámetros cinéticos estimados. Los keys
                son 'alfa', 'potencia', 'fq' y 'efi_over_beta2'. Los últimos
                dos son None en caso de ajustar una NCPSD
        """

        if self.fit_results is None:
            raise NameError("Faltan hacer el ajuste de los espectros")

        # Constantes cinéticas
        DIVEN = reactor.FACTOR_DIVEN
        BETA = reactor.BETA_EFECTIVO
        FORMA = reactor.FACTOR_FORMA_L
        EFISION = reactor.ENERGIA_FISION
        BENNETT = reactor.FACTOR_BENNETT

        self.parametros_cineticos = []
        # Asocio con sus incertezas
        for i, res in enumerate(self.fit_results):
            # Valores estimados
            par_val = [res.params[s].value for s in res.var_names]
            if i != 2:
                #  Cálculo con NAPSD
                if "covar" in dir(res):
                    # Se obtiene la matríz de covarianza
                    alfa, amplitud, constante =  \
                      correlated_values(par_val, res.covar, tags=res.var_names)
                else:
                    # No se obtiene matriz de covarianza
                    alfa, amplitud, constante = par_val
                    print(
                    "No se pudo estimar la matríz de covaarianza del ajuste")
                fq = constante * self.I[i] / 2
                efi_over_beta2 = amplitud * BENNETT / (1 - BETA) / FORMA \
                       / DIVEN / constante
            else:
                # Calculo con NCPSD
                if "covar" in dir(res):
                    # Se obtiene la matríz de covarianza
                    alfa, amplitud = correlated_values(par_val, res.covar,
                                                       tags=res.var_names)
                else:
                    # No se obtiene matriz de covarianza
                    alfa, amplitud = par_val
                    print(
                    "No se pudo estimar la matríz de covaarianza del ajuste")
                constante = None
                fq = None
                efi_over_beta2 = None
            # Cálculo de la potencia
            potencia = 2 * EFISION * DIVEN * (1 - BETA) * FORMA / BETA**2 \
                                                                    / amplitud

            # Salida
            _pars = {
                    "amplitud": amplitud,
                    "constante": constante,
                    "alfa": alfa,
                    "potencia": potencia,
                    "fq": fq,
                    "efi_over_beta2": efi_over_beta2,
                    }
            self.parametros_cineticos.append(_pars)


class RUIFileProcessing():
    """
    Procesamiento de los archivos .RUI generados por el programa FERCIN3

    Permite calcular los espectros, normalizarlos, graficarlos y obtener los
    parámetros cinéticos a partir del ajuste.

    Parameters
    ----------
        file_name : str
            Nombre del archivo en formato hdf5
        resolution: int
            Resolución del ADC con que se adquirió. Si no se especifica, se la
            trata de estimar en base a los valores registrados (elige entre 12
            y 16 bits).

    """

    def __init__(self, file_name, resolution=None):
        self.file_name = file_name

        self._read_file(self.file_name)

        current = os.path.dirname(os.path.realpath(__file__))
        parent = os.path.dirname(current)
        self.TRANSFERS_FOLDER = os.path.join(parent, "transferencias")

        if resolution is None:
            self.ADC_resolution = self._get_resolution()
        else:
            self.ADC_resolution = resolution
        self.norm_spectrums = None
        self.N_fft = None
        self.N_overlap = None
        self.fit_results = None


    def _read_file(self, file_name):
        with open(file_name, 'r') as f:
            # Date
            self.date = f.readline().rstrip('\n')
            # Hour
            self.hour = f.readline().rstrip('\n')
            # Number of AC data
            self.num_datos = int(float(f.readline().rstrip('\n')))

            tmp = [float(it) for it in f.readline().split()]
            # dt 
            self.dt = tmp[0]
            # Band width
            self.BW = 1 / (2 * self.dt)
            # Ip current and error [A]
            self.Ip = ufloat(tmp[1], tmp[2])
            # Number of detectores
            self.n_det = int(f.readline().strip('\n'))
            # Acquisition death time [s]
            self.death_time = float(f.readline().strip('\n'))
            # Rango/s de la adquisición [V]
            self.rango = [f.readline().split()[0]]
            if self.n_det == 2:
                self.rango.append(f.readline().split()[0])

            # ---- Detectors 
            # Comment
            self.comment = [f.readline().strip('\n')]
            tmp = [float(it) for it in f.readline().split()]
            # DC voltage [V]
            self.DC_volts = [ufloat(tmp[0], tmp[1])]
            # Background current [A]
            self.If = [ufloat(tmp[2], tmp[3])]
            tmp = [float(it) for it in f.readline().split()]
            # Impedance amplifier
            self.Z = [ufloat(tmp[0], tmp[1])]
            tmp = [float(it) for it in f.readline().split()]
            # AC gain
            self.K = [ufloat(tmp[0], tmp[1])]

            if self.n_det == 2:
                self.comment.append(f.readline().strip('\n'))
                tmp = [float(it) for it in f.readline().split()]
                # DC voltage [V]
                self.DC_volts.append(ufloat(tmp[0], tmp[1]))
                # Background current [A]
                self.If.append(ufloat(tmp[2], tmp[3]))
                tmp = [float(it) for it in f.readline().split()]
                # Impedance amplifier
                self.Z.append(ufloat(tmp[0], tmp[1]))
                tmp = [float(it) for it in f.readline().split()]
                # AC gain
                self.K.append(ufloat(tmp[0], tmp[1]))

            # AC data in int16 representation
            if self.n_det == 2:
                skip_hdr = 16
                rui_data = np.loadtxt(file_name, skiprows=skip_hdr)
                # AC data from CIC are alternated
                self.AC_int = [rui_data[0:][::2], rui_data[1:][::2]]
            else:
                skip_hdr = 12
                rui_data = np.loadtxt(file_name, skiprows=skip_hdr)
                self.AC_int = [rui_data[0:]]
        # Calculo las corrientes DC de cada cadena
        self.I = []
        for i in range(self.n_det):
            self.I.append(self.DC_volts[i] / self.Z[i] - self.If[i])


    def _get_resolution(self):
        """ Guess between 12 and 16 bits resolution """
        for dat in self.AC_int:
            if any(dat > 2**12):
                return 16
            else:
                print(
                "Resolución estimada de la ADC: 12 bits (podría estar mal)")
                return 12


    def get_temporal_signals(self):
        """ Calcula las AC en voltaje. Convierte dependiendo ADC """
        AC_volts = []
        if self.ADC_resolution == 12:
            # PCL818
            for i in range(self.n_det):
                rango = float(self.rango[i])
                AC_volts.append(
                    (self.AC_int[i] - 2**11) * 2 * rango / 2**12
                                )
        elif self.ADC_resolution == 16:
            for i in range(self.n_det):
                AC_volts.append(self.raw_to_volt_NI(
                                        self.AC_int[i] - 2**15, self.rango[i]
                                                    ))
        else:
            raise ValueError(f"No está contemplada una resolución de " +
                             f"{self.ADC_resolution} para la ADC")
        # Vector temporal
        time_vec = np.arange(0, len(AC_volts[0])) * self.dt
        return time_vec, AC_volts, None


    def get_spectrums(self, N_fft=None, N_overlap=None):
        """
        Espectros sin normalizar ni corregidos con función transferencia

        Son los valores que se guardan en los archivos .PSD con fercin3/5

        Los valores temporales del .RUI se transforman a voltaje, y se estima
        el espectro con el estimador de Welch utilizando N_fft puntos y
        N_overlap puntos de solapamiento.

        Returns:
            self.spectrums: lists of numpy arrays
                Lista con los espectros [APSD1, APSD2, CPSD]
            self.f: numpy array
                Vector con las frecuencias asociada a los espectros
        """
        if (N_fft is None) or (N_overlap is None):
            raise ValueError("Faltan especificar N_fft o N_overlap")

        self.N_fft = N_fft
        self.N_overlap = N_overlap

        VC_volts = []
        for i in range(self.n_det):
            VC_volts.append(self.DC_volts[i] - self.If[i] * self.Z[i])

        _, AC_volts, _ = self.get_temporal_signals()

        spectrums = []
        for AC in AC_volts:
            # Estimación de las APSD
            f_spectrums, _spec = signal.welch(AC, fs=1/self.dt,
                                      noverlap=N_overlap, nperseg=N_fft)
            spectrums.append(_spec)
        if self.n_det == 2:
            # Estimación de la CPSD
            _, _spec = signal.csd(AC_volts[0], AC_volts[1], fs=1/self.dt,
                                  noverlap=N_overlap, nperseg=N_fft)
            spectrums.append(_spec)
        self.spectrums = spectrums
        # Se convierten
        self.f = np.asarray(f_spectrums)
        return self.spectrums, self.f


    def get_normalized_spectrums(self, reactor_name, N_fft=None,
                                N_overlap=None, freqs_to_remove=[50, 100, 150],
                                freqs_to_remove_tr=[50, 100, 150]):
        """
        Calcula los espectros normalizados con el método de Welch.

        Se les quita las frencuencia de línea y sus dos armónicos.
        Están corregidos por la función transferencia.

        Si no se especifica N_fft y N_overlap se usan los espectros estimados
        con .get_spectrum(). Si se especifican, se vuelven a calcular.

        Parameters
        ----------
            N_fft: int
                Puntos para calcular la FFT en cada bloque
            N_overlap: int
                Cantidad de puntos para el solapamiento de bloques
            reactor_name: string
                Identificación del reactor (para leer transferencias)
            freqs_to_remove: list of floats
                Frecuencias que serán eliminadas del espectro medido
            freqs_to_remove: list of floats
                Frecuencias que serán eliminadas de las transferencias

        Returns
        -------
            self.spectrums: listr of numpy arrays
                Lista con los espectros [NPSD1, NPSD1, NCPSD12]
                Los NPSD son reales, la NCPSD es compleja
            self.f: numpy array
                Frecuencias asociadas a los espectros
        """

        # Si no se calcularon los espectros previamente, se los calcula
        if not hasattr(self, 'spectrums'):
            self.get_spectrums(N_fft, N_overlap)
        else:
            # Si se especifican los valores
            if N_fft or N_overlap:
                self.get_spectrums(N_fft, N_overlap)
        # Nombres de las funciones transferencia que voy a leer
        _tr_names = self._get_transfer_name(reactor_name)

        norm_spec = []
        _trans = []
        for i, _tr_name in enumerate(_tr_names):
            # Lectura de las funciones transferencia
            try:
                H2_dB, ReH, ImH = self._get_transfer_function(_tr_name,
                                                freqs_to_remove_tr)
            except IOError:
                _tr_name = os.path.join('..', _tr_name)
                H2_dB, ReH, ImH = self._get_transfer_function(_tr_name,
                                                freqs_to_remove_tr)

            # Módulo cuadrado de la función transferencia
            H2 = 10**(H2_dB / 10)
            _trans.append([H2, ReH, ImH])
            print(f"Se lee la función transferencia de {_tr_name}")
            # Espectro APSD
            APSD = self.spectrums[i]
            # En algunos casos del RA1 no coinciden los tamaños entre APSD y
            # la función tansferencia
            len_s, len_h = len(APSD), len(H2)
            if len_s != len_h:
                _min = min(len_s, len_h)
                f = f[:_min]
                APSD = APSD[:_min]
                H2 = H2[:_min]
                print(80*'!')
                msg = "Advertencia: el tamaño de la función transferencia\n"
                msg += "no coincide con el tamaño del espectro medido \n"
                msg += "Se toma el mínimo entre ambos: {}"
                print(msg.format(_min))
                print(80*'!')
            # Corrección por función transferencia
            APSD_tr = APSD / H2
            # Normalizo 
            V_sin_fondo = self.DC_volts[i] - self.If[i] * self.Z[i]
            NAPSD_tr = APSD_tr / V_sin_fondo**2
            # Quito frecuencias de línea
            NAPSD_tr = self._remove_utility_freq(
                                    self.f, NAPSD_tr, freqs_to_remove)
            # Los espectros tienen incertezas debido a la propagación, pero las
            # descarto por ahora:
            NAPSD_tr = unumpy.nominal_values(NAPSD_tr)
            norm_spec.append(NAPSD_tr)
        if len(_tr_names) == 2:
            # --- Corrección para la CPSD
            # Espectros sin corregir
            APSD1 = self.spectrums[0]
            APSD2 = self.spectrums[1]
            ReCPSD = np.real(self.spectrums[2])
            ImCPSD = np.imag(self.spectrums[2])
            # Funciones transferencia leidas anteriormente
            H2_1, ReH_1, ImH_1 = _trans[0]
            H2_2, ReH_2, ImH_2 = _trans[1]
            # Corrección de la CPSD por función transferencia
            _c1 = ReH_1 * ReH_2 + ImH_1 * ImH_2
            _c2 = ImH_1 * ReH_2 - ReH_1 * ImH_2
            ReCPSD_tr = (_c1 * ReCPSD - _c2 * ImCPSD) / (H2_1 * H2_2)
            ImCPSD_tr = (_c1 * ImCPSD + _c2 * ReCPSD) / (H2_1 * H2_2)
            # Normalizo con valor medio
            # Resto el fondo al voltaje medio
            V1_sf = self.DC_volts[0] - self.If[0] * self.Z[0]
            V2_sf = self.DC_volts[1] - self.If[1] * self.Z[1]
            ReNCPSD_tr = ReCPSD_tr / (V1_sf * V2_sf)
            ImNCPSD_tr = ImCPSD_tr / (V1_sf * V2_sf)
            # Quito frecuencias de línea
            ReNCPSD_tr = self._remove_utility_freq(self.f, ReNCPSD_tr,
                                                  freqs_to_remove)
            ImNCPSD_tr = self._remove_utility_freq(self.f, ImNCPSD_tr,
                                                  freqs_to_remove)
            # Los espectros tienen incertezas debido a la propagación, pero las
            # descarto por ahora:
            ReNCPSD_tr = unumpy.nominal_values(ReNCPSD_tr)
            ImNCPSD_tr = unumpy.nominal_values(ImNCPSD_tr)
            # Guardo el espectro complejo
            norm_spec.append(ReNCPSD_tr + 1j * ImNCPSD_tr)
        self.norm_spectrums = norm_spec
        return self.norm_spectrums, self.f


    def _get_transfer_name(self, reactor_name):
        """
        Get names of transfer functions
        """
        # FOLDER_NAME = "transferencias"
        if reactor_name:
            sub_folder = reactor_name
        else:
            sub_folder = ""

        path_file = []
        for i, K in enumerate(self.K):
            K_over_100 = np.round(K.n / 100)
            if i !=3:
                file_name = "TR{:.0f}{:.0f}A{}.PSD".format(
                            K_over_100, self.BW, i+1)
                path_file.append(os.path.join(self.TRANSFERS_FOLDER,
                                 sub_folder, file_name))
        return path_file


    def _get_transfer_function(self, file_name, freqs_to_remove=[50, 100, 150]):
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
        H2_dB = self._remove_utility_freq(freq, H2_dB, freqs_to_remove)
        ReH = self._remove_utility_freq(freq, ReH, freqs_to_remove)
        ImH = self._remove_utility_freq(freq, ImH, freqs_to_remove)
        return H2_dB, ReH, ImH


    def _remove_utility_freq(self, frequency, spectrum, freqs_to_remove):
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


    def plot_spectrums(self, normalizados=True, *args, **kargs):
        if normalizados:
            if self.norm_spectrums is None:
                raise NameError("Faltan estimar los espectros normalizados")
            _datas = self.norm_spectrums
            _labels = ["NPSD1", "NPSD2", "Re(NCPSD12)"]
            _units = "[1 / Hz]"
        else:
            if self.spectrums is None:
                raise NameError("Faltan estimar los espectros")
            _datas = self.spectrums
            _labels = ["PSD1", "PSD2", "Re(CPSD12)"]
            _units = "[V$^2$ / Hz]"

        figs, ax = plt.subplots(1, 1)

        for i, data in enumerate(_datas):
            if i == 2:
                data = np.real(data)
            ax.plot(self.f, data, '.-', label=_labels[i])
        ax.set_xlabel("Frecuencia [Hz]")
        ax.set_ylabel("Espectro " + _units)
        ax.legend()
        ax.set_title(f"Archivo leido: {self.file_name}")
        figs.tight_layout()

        plt.show()


    def fit_spectrums(self, intervals, **kargs):
        """
        Ajuste de los espectros

        intervals: list of tuples
            Lista con los límitesde los intervalos para el ajuste
            [(f_min, f_max), (f_min, f_max), ...]
            en el orden [NPSD1, NPSD2, CPSD12]
        kargs:
              plot: bool
                True si se quiere graficar. False por default
        """

        if self.norm_spectrums is None:
            raise NameError("Faltan estimar los espectros normalizados")

        plot = kargs.get('plot', False)
        _ttle = ["NPSD1", "NPSD2", "Re(NCPSD12)"]
        _ylab = [i + " [1 / Hz]" for i in _ttle]

        self.fit_results = []
        self.fitted_data = []
        for i, (spe, inter) in enumerate(zip(self.norm_spectrums, intervals)):
            ind = (self.f >= inter[0]) & (self.f <= inter[1])
            if i != 2:
                _dat = spe[ind]
                _res = ajuste_apsd(self.f[ind], _dat)
            else:
                _dat = np.real(spe[ind])
                _res = ajuste_cpsd(self.f[ind], _dat)
            self.fit_results.append(_res)
            self.fitted_data.append([self.f[ind], _dat])

            if plot:
                best_fit = _dat + _res.residual
                fig, (ax0, ax1) = plt.subplots(2, sharex=True,
                               gridspec_kw={'height_ratios': [3,1]},)
                ax0.errorbar(self.f, np.real(spe), fmt='k.', elinewidth=2,
                             label='Medición')
                ax0.plot(self.f[ind], best_fit, 'r', zorder=3, label='fit')
                ax0.set_ylabel(_ylab[i])

                ax1.plot(self.f[ind], _res.residual, 'k.')
                ax1.set_xlabel('f [Hz]')
                ax1.set_ylabel(r'Residuos [1/Hz]')
                ax0.set_title(f"Ajuste de {_ttle[i]}")
                fig.subplots_adjust(hspace=0.1)

        if plot: plt.show()


    def calcula_parametros_cineticos(self, reactor, **kwargs):
        """
        Calcula parámetros cinéticos en base al ajuste espectral

        Parameters
        ----------
            reactor: reactor class
                Clase importada del archivo "constantes_reactores.py"

        Returns
        -------
            self.parametros_cineticos: dic
                Diccionario con los parámetros cinéticos estimados. Los keys
                son 'alfa', 'potencia', 'fq' y 'efi_over_beta2'. Los últimos
                dos son None en caso de ajustar una NCPSD
        """

        if self.fit_results is None:
            raise NameError("Faltan hacer el ajuste de los espectros")

        # Constantes cinéticas
        DIVEN = reactor.FACTOR_DIVEN
        BETA = reactor.BETA_EFECTIVO
        FORMA = reactor.FACTOR_FORMA_L
        EFISION = reactor.ENERGIA_FISION
        BENNETT = reactor.FACTOR_BENNETT

        self.parametros_cineticos = []
        # Asocio con sus incertezas
        for i, res in enumerate(self.fit_results):
            # Valores estimados
            par_val = [res.params[s].value for s in res.var_names]
            if i != 2:
                #  Cálculo con NAPSD
                if "covar" in dir(res):
                    # Se obtiene la matríz de covarianza
                    alfa, amplitud, constante =  \
                      correlated_values(par_val, res.covar, tags=res.var_names)
                else:
                    # No se obtiene matriz de covarianza
                    alfa, amplitud, constante = par_val
                    print(
                    "No se pudo estimar la matríz de covaarianza del ajuste")
                fq = constante * self.I[i] / 2
                efi_over_beta2 = amplitud * BENNETT / (1 - BETA) / FORMA \
                       / DIVEN / constante
            else:
                # Calculo con NCPSD
                if "covar" in dir(res):
                    # Se obtiene la matríz de covarianza
                    alfa, amplitud = correlated_values(par_val, res.covar,
                                                       tags=res.var_names)
                else:
                    # No se obtiene matriz de covarianza
                    alfa, amplitud = par_val
                    print(
                    "No se pudo estimar la matríz de covaarianza del ajuste")
                constante = None
                fq = None
                efi_over_beta2 = None
            # Cálculo de la potencia
            potencia = 2 * EFISION * DIVEN * (1 - BETA) * FORMA / BETA**2 \
                                                                    / amplitud

            # Salida
            _pars = {
                    "amplitud": amplitud,
                    "constante": constante,
                    "alfa": alfa,
                    "potencia": potencia,
                    "fq": fq,
                    "efi_over_beta2": efi_over_beta2,
                    }
            self.parametros_cineticos.append(_pars)


    def raw_to_volt_NI(self, raw_data, volt_range):
        """
        Values for converting integer values into volt for the NI 6353 board

        The conversion is performed according to:
            f(x) = a[0]x^0 + a[1]x^1 + a[2]*x^2 + a[3]*x^3

        where 'x' is the raw data measured, 'a' are the coefficients given by
        the board specifications and f(x) is the data in Volts units.

        With the NI 6353 (PCI and USB?) the range is alwas bipolar (why?). The
        data in the .RUI file is converted to unipolar by adding 32768. So this
        last value should be substracted before calling this function.

        See Anexo 1 of IN-EN-GRYCN-FER-012_Rev0 for more info.

        Parameters
        ----------
            raw_data : array
                Raw data measured by the board
            volt_range : string
                Range used for the measurement ('10', '5', '2', '1', '.5',
                                                '.2' and '.1')

        Returns
        -------
            volt_data : array
                Voltage converted
        """

        try:
            # Se trata de leer el archivo con los coeficientes
            # Archivo generado en el momento de la adquisición (con programa
            # nuevo)
            data_folder = os.path.dirname(self.file_name)
            name_c = self.file_name.split('-')[0] + \
                                                "-coeficientes_int_to_volt.pkl"
            coef_file = os.path.join(data_folder, name_c)
            with open(coef_file, 'rb') as f:
                conversion = pickle.load(f)
            print("Se usan coenficientes de conversión a voltaje del",
                  f"archivo {coef_file}")
        except IOError:
            # Se usan unos valores de la NI USB-6353.
            # Debido a que si no se guardaron en el momento de la adquisición,
            # los .RUI no tienen esta información.
            conversion = {
                        .1: [-3.482209127662006e-05, 3.2165366451149876e-06,
                             -2.6971282517362403e-16, 7.29540470181873e-20],
                        .2: [-6.136419891439307e-05, 6.442667885061415e-06,
                             -5.402301756997927e-16, 1.4612570838363108e-19],
                        .5: [-0.0001385744440899197, 1.6111197802991186e-05,
                             -1.3509551283910506e-15, 3.6541697226543377e-19],
                        1.0: [-0.00026948936905494587, 3.222353064123045e-05,
                              -2.702005431685175e-15, 7.308596881874746e-19],
                        2.0: [-0.0005310680905440859, 6.443202206542382e-05,
                              -5.4027497959046236e-15, 1.4613782729249057e-18],
                        5.0: [-0.0013130513105791529, 0.00016106960701858363,
                              -1.3505998392576855e-14, 3.653208708652728e-18],
                        10.0: [-0.0026160260933094583, 0.0003222353136881715,
                               -2.702005492694728e-14, 7.308597046898186e-18],
                         }
            print("Se usan coenficientes de conversión a voltaje genéricos")
        _volt_float = float(volt_range)
        if _volt_float not in conversion.keys():
            raise KeyError(f"The range {volt_range} not available for the",
                           f"NI6353 board")
        else:
            volt_data = 0.0
            for k, c in enumerate(conversion[_volt_float]):
                volt_data +=  c * raw_data**k
            return volt_data


class FitResults():
    """
    Entre otras cosas, esta clase selecciona qué mediciones se utilizan para
    calcular ciertos parámetros (alfas, fq, etc). Por ejemplo, aquí se
    especifica que los fq se calculen sólo con las mediciones de 200Hz.
    """


    def __init__(self, file_name_pkl=None):
        if file_name_pkl:
            self.file_name_pkl = file_name_pkl
            try:
                with open(self.file_name_pkl, "rb") as f:
                    self.data = pickle.load(f)
            except IOError:
                raise IOError(
                f"FileResults no pudo abrir el archivo {self.file_name_pkl}")

        #self.data = np.asarray(self.data)
        columns = ["Nivel", "Medición", "BW", "Espectro", "Ip", "Ii", "Alfa",
                   "Potencia", "fq", "efi/b2"]
        # Trabajo con una DataFrame de panda
        df = pd.DataFrame(self.data, columns=columns)
        if len(df.Espectro.unique()) == 3:
            self.n_det = 2
        else:
            self.n_det = 1

        # Alfas calculados con detector 1 a 40Hz
        self.alfa_1 = df[df["Espectro"]=="NPSD1"]["Alfa"]
        # Alfas calculados con detector 2 a 40Hz
        self.alfa_2 = df[df["Espectro"]=="NPSD2"]["Alfa"]
        # Alfas calculados con CPSD a 40Hz
        self.alfa = df[df["Espectro"]=="NCPSD"]["Alfa"]
        self.alfas = [self.alfa_1, self.alfa_2, self.alfa]

        # Poetncias calculadas con detector 1
        self.pote_1 = df[df["Espectro"]=="NPSD1"]["Potencia"]
        # Poetncias calculadas con detector 2
        self.pote_2 = df[df["Espectro"]=="NPSD2"]["Potencia"]
        # Poetncias calculadas con CPSD
        self.pote = df[df["Espectro"]=="NCPSD"]["Potencia"]
        self.potencias = [self.pote_1, self.pote_2, self.pote]

        if self.n_det == 2:
            self.pote_bylevel = df[df["Espectro"]=="NCPSD"].groupby(
            "Nivel")["Potencia"].apply(unumpy.nominal_values).apply(np.mean)
            self.alfa_bylevel = df[df["Espectro"]=="NCPSD"
                                     ].groupby("Nivel")["Alfa"]
        elif self.n_det == 1:
            self.pote_bylevel = df[df["Espectro"]=="NPSD1"].groupby(
            "Nivel")["Potencia"].apply(unumpy.nominal_values).apply(np.mean)
            self.alfa_bylevel = df[df["Espectro"]=="NPSD1"
                                     ].groupby("Nivel")["Alfa"]

        # Fq
        fq_1 = df[(df["Espectro"]=="NPSD1") & (df["BW"]==200)]["fq"]
        fq_2 = df[(df["Espectro"]=="NPSD2") & (df["BW"]==200)]["fq"]
        self.fqs = [fq_1, fq_2]
        self.I_fq1 = df[(df["Espectro"]=="NPSD1") & (df["BW"]==200)]["Ii"]
        self.I_fq2 = df[(df["Espectro"]=="NPSD2") & (df["BW"]==200)]["Ii"]

        self.fq_1_bylevel = df[(df["Espectro"]=="NPSD1") &
                                        (df["BW"]==200)].groupby("Nivel")["fq"]
        self.fq_2_bylevel = df[(df["Espectro"]=="NPSD2") &
                                        (df["BW"]==200)].groupby("Nivel")["fq"]

        # Eficiencia dividio beta cuadrado
        efi_b2_1 = df[(df["Espectro"]=="NPSD1") & (df["BW"]==200)]["efi/b2"]
        efi_b2_2 = df[(df["Espectro"]=="NPSD2") & (df["BW"]==200)]["efi/b2"]
        self.efi_b2s = [efi_b2_1, efi_b2_2]

        self.efi_1_bylevel = df[(df["Espectro"]=="NPSD1") &
                                    (df["BW"]==200)].groupby("Nivel")["efi/b2"]
        self.efi_2_bylevel = df[(df["Espectro"]=="NPSD2") &
                                    (df["BW"]==200)].groupby("Nivel")["efi/b2"]
        # Corrientes
        self.I1 = df[df["Espectro"]=="NPSD1"]["Ii"]
        self.I2 = df[df["Espectro"]=="NPSD2"]["Ii"]
        self.Ip = df[df["Espectro"]=="NPSD1"]["Ip"]
        self.Is = [self.I1, self.I2, self.Ip]


    def simulate_data_S19(self):
        """
        Datos medidos en el RA-3 con dos detectores (serie 19)
        """
        dat = []
        dat.append([1, 1, 200, "NPSD1", '', '', '', '', '', ''])
        dat.append([1, 1, 200, "NPSD2", '', '', '', '', '', ''])
        dat.append([1, 1, 200, "NCPSD", '', None, '', '', None, None])
        dat.append([1, 2,  40, "NPSD1", '', '', '', '', '', ''])
        dat.append([1, 2,  40, "NPSD2", '', '', '', '', '', ''])
        dat.append([1, 2,  40, "NCPSD", '', None, '', '', None, None])
        dat.append([1, 3,  40, "NPSD1", '', '', '', '', '', ''])
        dat.append([1, 3,  40, "NPSD2", '', '', '', '', '', ''])
        dat.append([1, 3,  40, "NCPSD", '', None, '', '', None, None])
        dat.append([2, 1, 200, "NPSD1", '', '', '', '', '', ''])
        dat.append([2, 1, 200, "NPSD2", '', '', '', '', '', ''])
        dat.append([2, 1, 200, "NCPSD", '', None, '', '', None, None])
        dat.append([2, 2,  40, "NPSD1", '', '', '', '', '', ''])
        dat.append([2, 2,  40, "NPSD2", '', '', '', '', '', ''])
        dat.append([2, 2,  40, "NCPSD", '', None, '', '', None, None])
        dat.append([2, 3,  40, "NPSD1", '', '', '', '', '', ''])
        dat.append([2, 3,  40, "NPSD2", '', '', '', '', '', ''])
        dat.append([2, 3,  40, "NCPSD", '', None, '', '', None, None])
        dat.append([3, 1, 200, "NPSD1", '', '', '', '', '', ''])
        dat.append([3, 1, 200, "NPSD2", '', '', '', '', '', ''])
        dat.append([3, 1, 200, "NCPSD", '', None, '', '', None, None])
        dat.append([3, 2,  40, "NPSD1", '', '', '', '', '', ''])
        dat.append([3, 2,  40, "NPSD2", '', '', '', '', '', ''])
        dat.append([3, 2,  40, "NCPSD", '', None, '', '', None, None])
        dat.append([3, 3,  40, "NPSD1", '', '', '', '', '', ''])
        dat.append([3, 3,  40, "NPSD2", '', '', '', '', '', ''])
        dat.append([3, 3,  40, "NCPSD", '', None, '', '', None, None])

        self.data = dat

        columns = ["Nivel", "Medición", "BW", "Espectro", "Ip", "Ii", "Alfa",
                   "Potencia", "fq", "efi/b2"]
        df = pd.DataFrame(dat, columns=columns)
        I1, _, I1_s = np.loadtxt(os.path.join("test","I1-S19.EST"), skiprows=5,
                                 delimiter=',', unpack=True)
        I2, _, I2_s = np.loadtxt(os.path.join("test","I2-S19.EST"), skiprows=5,
                                 delimiter=',', unpack=True)
        Ip, _, Ip_s = np.loadtxt(os.path.join("test","IP-S19.EST"), skiprows=5,
                                               delimiter=',', unpack=True)
        pot, _, pot_s = np.loadtxt(os.path.join("test","POTE-S19.EST"),
                                   skiprows=5, delimiter=',', unpack=True)
        pot1, pot1_s = np.loadtxt(os.path.join("test","P1I1-S19.LIN"),
                                  skiprows=3, delimiter=',', unpack=True)
        pot1 = pot1[1::2]
        pot1_s = pot1_s[1::2]
        pot2, pot2_s = np.loadtxt(os.path.join("test","P2I1-S19.LIN"),
                                  skiprows=3, delimiter=',', unpack=True)
        pot2 = pot2[1::2]
        pot2_s = pot2_s[1::2]
        alfa, _, alfa_s = np.loadtxt(os.path.join("test","ALFA-S19.EST"),
                                     skiprows=5, delimiter=',', unpack=True)
        alfa1, _, alfa1_s = np.loadtxt(os.path.join("test","ALF1-S19.EST"),
                                       skiprows=5, delimiter=',', unpack=True)
        alfa2, _, alfa2_s = np.loadtxt(os.path.join("test","ALF2-S19.EST"),
                                       skiprows=5, delimiter=',', unpack=True)
        fq1, _, fq1_s = np.loadtxt(os.path.join("test","FQ1-S19.EST"),
                                   skiprows=5, delimiter=',', unpack=True)
        fq1 = fq1 * 1E-15
        fq1_s = fq1_s * 1E-15
        fq2, _, fq2_s = np.loadtxt(os.path.join("test","FQ2-S19.EST"),
                                   skiprows=5, delimiter=',', unpack=True)
        fq2 = fq2 * 1E-15
        fq2_s = fq2_s * 1E-15
        efi1, _, efi1_s = np.loadtxt(os.path.join("test","EF1B-S19.EST"),
                                     skiprows=5, delimiter=',', unpack=True)
        efi2, _, efi2_s = np.loadtxt(os.path.join("test","EF2B-S19.EST"),
                                     skiprows=5, delimiter=',', unpack=True)

        uI1 = []
        for n, s in zip(I1, I1_s):
            uI1.append(ufloat(n, s))
        uI2 = []
        for n, s in zip(I2, I2_s):
            uI2.append(ufloat(n, s))
        uIp = []
        for n, s in zip(Ip, Ip_s):
            uIp.append(ufloat(n, s))
        upot = []
        for n, s in zip(pot, pot_s):
            upot.append(ufloat(n, s))
        upot1 = []
        for n, s in zip(pot1, pot1_s):
            upot1.append(ufloat(n, s))
        upot2 = []
        for n, s in zip(pot2, pot2_s):
            upot2.append(ufloat(n, s))
        ualfa = []
        for n, s in zip(alfa, alfa_s):
            ualfa.append(ufloat(n, s))
        ualfa1 = []
        for n, s in zip(alfa1, alfa1_s):
            ualfa1.append(ufloat(n, s))
        ualfa2 = []
        for n, s in zip(alfa2, alfa2_s):
            ualfa2.append(ufloat(n, s))
        ufq1 = []
        for n, s in zip(fq1, fq1_s):
            ufq1.append(ufloat(n, s))
        ufq2 = []
        for n, s in zip(fq2, fq2_s):
            ufq2.append(ufloat(n, s))
        uefi1 = []
        for n, s in zip(efi1, efi1_s):
            uefi1.append(ufloat(n, s))
        uefi2 = []
        for n, s in zip(efi2, efi2_s):
            uefi2.append(ufloat(n, s))

        df.loc[df["Espectro"]=="NPSD1", "Ii"] = uI1
        df.loc[df["Espectro"]=="NPSD2", "Ii"] = uI2
        df.loc[df["Espectro"]=="NPSD1", "Ip"] = uIp
        df.loc[df["Espectro"]=="NPSD2", "Ip"] = uIp
        df.loc[df["Espectro"]=="NCPSD", "Ip"] = uIp
        df.loc[df["Espectro"]=="NCPSD", "Potencia"] = upot
        df.loc[df["Espectro"]=="NPSD1", "Potencia"] = upot1
        df.loc[df["Espectro"]=="NPSD2", "Potencia"] = upot2
        df.loc[(df["Espectro"]=="NCPSD") & (df["BW"]==40), "Alfa"] = ualfa
        df.loc[(df["Espectro"]=="NPSD1") & (df["BW"]==40), "Alfa"] = ualfa1
        df.loc[(df["Espectro"]=="NPSD2") & (df["BW"]==40), "Alfa"] = ualfa2
        df.loc[(df["Espectro"]=="NPSD1") & (df["BW"]==200), "fq"] = ufq1
        df.loc[(df["Espectro"]=="NPSD2") & (df["BW"]==200), "fq"] = ufq2
        df.loc[(df["Espectro"]=="NPSD1") & (df["BW"]==200), "efi/b2"] = uefi1
        df.loc[(df["Espectro"]=="NPSD2") & (df["BW"]==200), "efi/b2"] = uefi2
        df.replace("", np.nan, inplace=True)
        self.data = df
        with open("S19-fit_results.pkl", "wb") as f:
            pickle.dump(df.to_numpy(), f)


    def fit_p_vs_I(self, limites=None, plot=True, *args, **kargs):
        """
        Se hacen todos los ajustes lineales de corrientes y potencias

        p vs I1, p vs I2, p vs Ip

        """
        if not hasattr(self, '_I_mag'):
            self._I_mag, self._I_std = self._split_pandas_ufloat(self.Is)
        if not hasattr(self, '_pot_mag'):
            self._pots_mag, self._pots_std = \
                                      self._split_pandas_ufloat(self.potencias)
            # Para saber qué potencia usar para el ajuste
            # Si existe, tomo la calculada con NCPSD, de lo contrario con NPSD1
            ind_spec = 2 if self._pots_mag[2].size > 0 else 0
            # Selecciono la potencia para el ajuste
            self._pot_mag = self._pots_mag[ind_spec]
            self._pot_std = self._pots_std[ind_spec]
        if limites is None:
            limites = []
            for curr in self._I_mag:
                if curr.size > 0:
                    limites.append([np.min(curr), np.max(curr)])
                else:
                    limites.append([])
        labels = ["I$_1$ [A]", "I$_2$ [A]", "I$_p$ [A]"]
        # Ajustes lineales
        fited_p_vs_I = []
        for k, (cu, cu_s) in enumerate(zip(self._I_mag, self._I_std)):
            # Ajustes
            if cu.size > 0:
                # Límites del ajuste
                I1, I2 = limites[k]
                ind = (cu >= I1) & (cu <= I2)
                # Ajuste de p vs I
                a, b, r_2, cov, y_fit = ajuste_lineal(
                        cu[ind], self._pot_mag[ind], self._pot_std[ind])
                fited_p_vs_I.append([a, b, r_2, cov, y_fit])
                if plot:
                    fig, ax = plt.subplots(1, 1)
                    ax.errorbar(cu, self._pot_mag, xerr=cu_s,
                                                yerr=self._pot_std, fmt='ok')
                    ax.plot(cu[ind], y_fit, 'r-')
                    ax.set_xscale('log')
                    ax.set_yscale('log')
                    ax.set_xlabel(labels[k])
                    ax.set_ylabel("p [W]")
                    # En el gráfico
                    str_a = f"a = ${a:.2uL}$ W/A\n"
                    str_b = f"b = ${b:.2uL}$ W/A\n"
                    str_r2 = f"r$^2$ = ${r_2:1.5f}$"
                    bbox_props = dict(boxstyle='Round', fc='w')
                    ax.annotate(str_a + str_b + str_r2,
                    xy=(0.4, 0.15), bbox=bbox_props,
                    size=12, xycoords='axes fraction')
                    fig.tight_layout()
            else:
                # Para respetar el orden [f1, f2, fp]
                fited_p_vs_I.append([[]])
            # Graficos
        self.fited_p_vs_I = np.asarray(fited_p_vs_I, dtype=object)
        plt.show()


    def fit_Ip_vs_I(self, limites=None, plot=True, *args, **kargs):
        """
        Se hacen todos los ajustes lineales entre corrientes

        Ip vs I1, Ip vs I2

        """
        if not hasattr(self, "_I_mag"):
            self._I_mag, self._I_std = self._split_pandas_ufloat(self.Is)
        if limites is None:
            limites = []
            for curr in self._I_mag[:-1]:
                if curr.size > 0:
                    limites.append([np.min(curr), np.max(curr)])
                else: limites.append([])

        labels = ["I$_1$ [A]", "I$_2$ [A]", "I$_p$ [A]"]
        # Ajustes lineales
        fit_Ip_vs_I = []
        for k, (cu, cu_s) in enumerate(zip(self._I_mag[:-1], self._I_std[:-1])):
            # Ajustes
            if cu.size > 0:
                # Límites del ajuste
                I1, I2 = limites[k]
                ind = (cu >= I1) & (cu <= I2)
                # Ajuste de p vs I
                a, b, r_2, cov, y_fit = ajuste_lineal(
                        cu[ind], self._I_mag[2][ind], self._I_std[2][ind])
                fit_Ip_vs_I.append([a, b, r_2, cov, y_fit])
                if plot:
                    fig, ax = plt.subplots(1, 1)
                    ax.errorbar(cu, self._I_mag[2], xerr=cu_s,
                                          yerr=self._I_std[2], fmt='ok')
                    ax.plot(cu[ind], y_fit, 'r-')
                    ax.set_xscale('log')
                    ax.set_yscale('log')
                    ax.set_xlabel(labels[k])
                    ax.set_ylabel("I$_p$ [A]")
                    # En el gráfico
                    str_a = f"a = ${a:.2uL}$ \n"
                    str_b = f"b = ${b:.2uL}$ \n"
                    str_r2 = f"r$^2$ = ${r_2:1.5f}$"
                    bbox_props = dict(boxstyle='Round', fc='w')
                    ax.annotate(str_a + str_b + str_r2,
                    xy=(0.4, 0.15), bbox=bbox_props,
                    size=12, xycoords='axes fraction')
                    fig.tight_layout()
            else:
                # Para respetar el orden 
                fit_Ip_vs_I.append([[]])
            # Graficos
        self.fit_Ip_vs_I = np.asarray(fit_Ip_vs_I, dtype=object)
        plt.show()


    def _split_pandas_ufloat(self, panda_serie):
        """
        Convierte una serie de panda con datos ufloat a dos arrays de numpy

        Uno es la magnitud y la otra su incerteza
        """
        mag, std = [], []
        for it in panda_serie:
            mag.append(unumpy.nominal_values(it.to_numpy()))
            std.append(unumpy.std_devs(it.to_numpy()))
        return mag, std


    def average_parameters(self, plot=True):
        """
        Hace los promedios pesados de a, fq y e/b2

        self.añfa_prom y self.alfa_std: floats
        self.fqs_av: list of touples (mag, std)
        self.eb2_av: list of touples (mag, std)
        """
        # ---- Alfas
        _alfas_mag, _alfas_std = self._split_pandas_ufloat(self.alfas)
        # Para saber qué alfas usar para el promedio
        # Si existen, tomo la calculada con NCPSD, de lo contrario con NPSD1
        ind_spec = 2 if _alfas_mag[2].size > 0 else 0
        # Selecciono la potencia para el ajuste
        self._alfa_mag = _alfas_mag[ind_spec]
        self._alfa_std = _alfas_std[ind_spec]

        self.alfa_prom, self.alfa_std = \
                      weighted_average(self._alfa_mag, 1.0 / self._alfa_std**2)
        # ----- fqs
        self._fqs_mag, self._fqs_std = self._split_pandas_ufloat(self.fqs)
        self.fqs_av = []
        for fq, fq_s in zip(self._fqs_mag, self._fqs_std):
            self.fqs_av.append(weighted_average(fq, 1 / fq_s**2))

        # ----- e/b2
        self._eb2_mag, self._eb2_std = self._split_pandas_ufloat(self.efi_b2s)

        self.eb2_av = []
        for eb2, eb2_s in zip(self._eb2_mag, self._eb2_std):
            self.eb2_av.append(weighted_average(eb2, 1 / eb2_s**2))

        if plot:
            # alfas
            alfa_lvl = self.alfa_bylevel.apply(unumpy.nominal_values)
            alfa_lvl_s = self.alfa_bylevel.apply(unumpy.std_devs)
            fig, ax = plt.subplots(1, 1)
            for p, a, a_s in zip(self.pote_bylevel, alfa_lvl, alfa_lvl_s):
                ax.errorbar(p * np.ones_like(a), a, yerr=a_s,
                                   fmt='ok', label="Con NCPSD a 40Hz")
            #   valor medio
            x = np.linspace(10, 10e3, 20)
            y = np.ones_like(x) * self.alfa_prom
            y_inf = np.ones_like(x) * (self.alfa_prom - self.alfa_std)
            y_sup = np.ones_like(x) * (self.alfa_prom + self.alfa_std)
            ax.plot(x, y, 'r-')
            ax.plot(x, y_inf, 'r--')
            ax.plot(x, y_sup, 'r--')

            handles, labels = ax.get_legend_handles_labels()
            ax.legend([handles[0]], [labels[0]])
            ax.set_xscale('log')
            ax.set_xlabel('Potencia [W]')
            ax.set_ylabel("$\\alpha$ [1/s]")
            ax.set_xlim(10, 10e3)
            a_uf = ufloat(self.alfa_prom, self.alfa_std)
            ax.set_title(f"$\\langle\\alpha\\rangle$ = {a_uf} 1/s")

            # fq1
            fq1 = self.fqs[0].apply(unumpy.nominal_values)
            fq1_s = self.fqs[0].apply(unumpy.std_devs)
            I_fq1 = self.I_fq1.apply(unumpy.nominal_values)
            fig, ax = plt.subplots(1, 1)
            ax.errorbar(I_fq1, fq1, yerr=fq1_s, fmt='ok', label="Detector 1")
            hand, lab = ax.get_legend_handles_labels()
            hand1, lab1 = hand[0], lab[0]
            uf1 = ufloat(*self.fqs_av[0])
            str_title1 = f"$\\langle f_{{q1}} \\rangle$ = {uf1} C"
            ax.set_title(str_title1)
            ax.legend([hand1], [lab1])
            ax.set_xscale('log')
            ax.set_xlabel('I$_1$ [A]')
            ax.set_ylabel("f$_q$ [C]")

            # fq2
            fq2 = self.fqs[1].apply(unumpy.nominal_values)
            fq2_s = self.fqs[1].apply(unumpy.std_devs)
            I_fq2 = self.I_fq2.apply(unumpy.nominal_values)
            if fq2.size > 0:
                fig, ax = plt.subplots(1, 1)
                ax.errorbar(I_fq2, fq2, yerr=fq2_s, fmt='ok',
                                                    label="Detector 2")
                hand, lab = ax.get_legend_handles_labels()
                hand2, lab2 = hand[-1], lab[-1]
                ax.legend([hand1, hand2], [lab1, lab2])
                uf2 = ufloat(*self.fqs_av[1])
                str_title2 = f"$\\langle f_{{q2}} \\rangle$ = {uf2} C"
                ax.set_title(str_title1 + '\t' + str_title2)
                ax.set_xscale('log')
                ax.set_xlabel('I$_2$ [A]')
                ax.set_ylabel("f$_q$ [C]")

            # efi/beta2 1
            efi1 = self.efi_1_bylevel.apply(unumpy.nominal_values)
            efi1_s = self.efi_1_bylevel.apply(unumpy.std_devs)
            fig, ax = plt.subplots(1, 1)
            for p, ef1, ef1_s in zip(self.pote_bylevel, efi1, efi1_s):
                ax.errorbar(p * np.ones_like(ef1), ef1, yerr=ef1_s, fmt='ok',
                            label="Detector 1")
            hand, lab = ax.get_legend_handles_labels()
            hand1, lab1 = hand[0], lab[0]
            ef1 = ufloat(*self.eb2_av[0])
            str_title1 = f"$\\langle \\epsilon_1/\\beta^2 \\rangle$ = {ef1}"
            # efi/beta2 2
            efi2 = self.efi_2_bylevel.apply(unumpy.nominal_values)
            efi2_s = self.efi_2_bylevel.apply(unumpy.std_devs)
            if fq2.size > 0:
                for p, ef2, ef2_s in zip(self.pote_bylevel, efi2, efi2_s):
                    ax.errorbar(p * np.ones_like(ef2), ef2, yerr=ef2_s,
                                                fmt='ob', label="Detector 2")
                hand, lab = ax.get_legend_handles_labels()
                hand2, lab2 = hand[-1], lab[-1]
                ax.legend([hand1, hand2], [lab1, lab2])
                ef2 = ufloat(*self.eb2_av[1])
                str_title2 = f"$\\langle \\epsilon_2/\\beta^2 \\rangle$ = {ef2}"
                ax.set_title(str_title1 + '\t' + str_title2)
            else:
                ax.legend([hand1], [lab1])
                ax.set_title(str_title1)
            ax.set_xscale('log')
            ax.set_xlabel('Potencia [W]')
            ax.set_ylabel(r"$\epsilon/\beta^2$")
            ax.set_xlim(10, 10e3)

            plt.show()


if __name__ == "__main__":
    current = os.path.dirname(os.path.realpath(__file__))
    parent = os.path.dirname(current)
    sys.path.append(parent)

    ##########################################################################
    # Prueba de clase HDF5FileProcessing
    ##########################################################################

    if False:
        from constantes.constantes_reactores import RA3 as REACTOR

        file_name = "S01-N1-1.h5"
        folder = os.path.join(parent, "gui")
        file_path = os.path.join(folder, file_name)

        rui = HDF5FileProcessing(file_path)

        print(f"Fecha: {rui.date}")
        print(f"Hora: {rui.hour}")
        print(f"Resolucion: {rui.resolucion_DAC}")
        print(f"Sensibilidades: {rui.sensibilidades}")
        print(f"DC {rui.DC_volts}")
        print(f"DC rangos {rui.DC_rangos}")
        print(f"Offsets {rui.offsets}")
        print(f"AC gains {rui.AC_gains}")
        print(f"Corrientes fondo {rui.If}")
        print(f"Corrientes DC {rui.I}")
        print(f"Corrientes Ip {rui.Ip}")

        # quit()
        # Espectros sin normalizar
        spect, fs = rui.get_spectrums(512, 0)
        # Espectros normalizados y corregidos por función transferencia
        norm_spect, fs = rui.get_normalized_spectrums("RA3",
                                        freqs_to_remove=[50, 100, 150])

        # Graficación de los espectros
        # rui.plot_spectrums(normalizados=True)
        # Intervalos para el ajuste
        if rui.BW == 200:
            intervalos = 2 * [(2.3, 178.9)] + [(2.3, 93)]
        elif rui.BW == 40:
            intervalos = 3 * [(2.8, 35.8)]

        rui.fit_spectrums(intervalos, plot=True)

        rui.calcula_parametros_cineticos(REACTOR)
        print(80*'-')
        for param in rui.parametros_cineticos:
            for key, val in param.items():
                if val:
                    print(key, f"{val:.3e}")
                else:
                    print(key, f"{val}")
            print(80*'-')
    ##########################################################################
    # Prueba de clase FitResults
    ##########################################################################
    if False:
        #filename = "S98-fit_results.pkl"   # Dos detectores RA-3
        filename = "S19-fit_results.pkl"  # Un detector RA-1
        fit_results = FitResults(filename)

        fit_results.fit_p_vs_I()
        for fps in fit_results.fited_p_vs_I:
            print(fps[0])
        fit_results.fit_Ip_vs_I(plot=True)

        fit_results.average_parameters(plot=True)

    ##########################################################################
    # Prueba de clase RUIFile
    ##########################################################################

    if True:
        from constantes.constantes_reactores import RA3 as REACTOR

        file_name = "S31-N3-1.RUI"
        folder = os.path.join(parent, "datos")
        file_path = os.path.join(folder, file_name)

        rui = RUIFileProcessing(file_path)

        print(f"Rangos utilizados: {rui.rango}")
        print(f"Resolución del ADC: {rui.ADC_resolution}")
        print(f"Corrientes: {rui.I}")

        rui.get_temporal_signals()

        # Espectros sin normalizar
        spect, fs = rui.get_spectrums(512, 0)
        # Espectros normalizados y corregidos por función transferencia
        norm_spect, fs = rui.get_normalized_spectrums("RA1",
                                        freqs_to_remove=[50, 100, 150])

        # Graficación de los espectros
        # rui.plot_spectrums(normalizados=True)
        # Intervalos para el ajuste
        rui.BW = round(rui.BW)
        if rui.BW == 200:
            intervalos = 2 * [(2.3, 178.9)] + [(2.3, 93)]
        elif rui.BW == 40:
            intervalos = 3 * [(2.8, 35.8)]

        rui.fit_spectrums(intervalos, plot=True)

        rui.calcula_parametros_cineticos(REACTOR)
        print(80*'-')
        for param in rui.parametros_cineticos:
            for key, val in param.items():
                print(key, val)
            print(80*'-')
