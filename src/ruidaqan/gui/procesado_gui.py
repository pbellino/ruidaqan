#! /usr/bin/env python3

from PyQt6.QtWidgets import (
        QWidget,
        QGridLayout,
        QLabel,
        QLCDNumber,
        QProgressBar,
        QMainWindow,
)
from PyQt6.QtCore import pyqtSignal, Qt, QSize, pyqtSlot
from PyQt6 import QtGui

import pyqtgraph as pg
import numpy as np
from.misc_functions import int_to_volt
from ruidaqan import DEBUG_MODE

class ShowRangesUtilization(QWidget):
    """
    Clase para mostrar la utilización de los rangos utilizados por la DAQ
    TODO
    """
    def __init__(self, cfg_adv):
        super().__init__()
        self.channels = cfg_adv.get_channels()
        self.labels = cfg_adv.get_channels_labels()

        self.init_ui()

    def init_ui(self):
        self.layout = QGridLayout()
        # Labels para cada columna
        labels_col = ["Canal", "Nombre", "Rango [V]", "Utilización"]

        # Agrego labels a los encabezados de columnas
        for i, label in enumerate(labels_col):
            _qlabel = QLabel(label)
            _qlabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.layout.addWidget(_qlabel, 0, i)
        for i, (name, label) in enumerate(zip(self.channels, self.labels)):
            # Columna con los canales
            _chan_name = QLabel(name.split('/')[-1])
            _chan_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.layout.addWidget(_chan_name, i + 1, 0)
            # Labels de los canales
            _chan_lbl = QLabel(label)
            _chan_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.layout.addWidget(_chan_lbl, i + 1, 1)
            # Label vacio para los rangos
            _empty_lab = QLabel()
            _empty_lab.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.layout.addWidget(_empty_lab, i + 1, 2)
            # Barras para utilización
            self.layout.addWidget(
                        QProgressBar(self, minimum=0, maximum=100, value=0),
                                 i + 1, 3)
        self.setLayout(self.layout)
        self.layout.setAlignment(
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)


    def update(self, ranges, utilization):
        for i, (rng, util) in enumerate(zip(ranges, utilization)):
            self.layout.itemAtPosition(i + 1, 2).widget().setText(f"{rng}")
            # Analizar por qué pide que sea entero al usar PyQt6
            # self.layout.itemAtPosition(i + 1, 3).widget().setValue(util)
            self.layout.itemAtPosition(i + 1, 3).widget().setValue(int(util))


class ProgresoMedicion(QWidget):
    """
    Clase para controlar y visualizar el progreso de la medición

    Se debe instanciar en cada medición.

    - Convierte de I16 a float
    - Muestra en pantalla valores de voltaje y corrientes promedio por historia
    - Comprueba la saturación de los rangos de los canales (en int16)
    - Comprueba la saturación a la entrada del anti-aliasing (en volts)
    - Lleva registro de lo adquirido

    Envía las siguientes señales:

    data_in_volts: en cada historia medida, Envia los datos convertidos a
    voltaje para su graficación

    all_histories_read: cuando se adquieren todas las hitorias solicitadas

    data_saturation(tipo, chns): cuando hay saturación. En "tipo" se indica
                     "Rango" -> Saturación en los rangos de la tarjeta
                     "AC_AA" -> Saturación en el filtro antialiasing
                     "chns": lista con índices de los canales saturados

    """

    # Señal para graficar los datos convertidos a voltaje
    data_in_volts = pyqtSignal(object)
    # Señal que se emite cuando todas las historias ya fueron adquiridas
    all_histories_read = pyqtSignal()
    # Señal para indicar que hay saturación, tanto en el rango de la tarjeta
    # como en la entrada del antialiasing
    data_saturation = pyqtSignal(str, list)
    # Señal para actualizar la ventana de control
    valores_control = pyqtSignal(int, list, list)

    def __init__(self, esp_med_par, cfg_adv, tipo_med=None, par_fondo=None):
        """
        tipo_med = "Fondo", "Rangos"
        """
        super().__init__()
        _res_ADC = cfg_adv.get_ADC_resolution()
        self.SATURATION_BIT = 2**(_res_ADC - 1) - 1
        self.SATURATION_AC_ANTIALIAS = 4.0   # Filtro AA satura en 4 volts
        # Canales
        self.channels = cfg_adv.get_channels()
        # Rangos
        self.ranges = cfg_adv.get_channels_ranges()
        # Coeficientes para convertir de I16 a voltaje
        self.coefs = cfg_adv.get_channels_coefs(self.channels, self.ranges)
        # Labels de cada canal
        self.labels = cfg_adv.get_channels_labels()
        # Tipo de medición
        self.tipo_med = tipo_med
        # Cantidad de cadenas utilizadas
        self.n_det = esp_med_par.n_det
        # Si se mide Cip
        self.cip = esp_med_par.cip
        if (self.tipo_med == "Fondo") or (self.tipo_med == "Rangos"):
            # Para medir fondo o ajuste de rangos uso valores constantes
            self.fs = par_fondo[0]
            self.pts_hist = par_fondo[1]
            self.tot_hist = par_fondo[2]
        else:
            # Frecuencia de muestreo (2 * BW)
            self.fs = 2 * esp_med_par.get_param_value("Parámetros medición",
                                                      "DAQ", "BW manual")
            # Cantidad de datos que por historia que serán adquiridos
            self.pts_hist = esp_med_par.get_param_value("Parámetros medición",
                                                        "DAQ", "Puntos")
            # Cantidad de historias que serán adquiridas
            self.tot_hist = esp_med_par.get_param_value("Parámetros medición",
                                                        "DAQ", "Historias")
        # Sensibilidad de los amplificadores para convertir el voltaje
        # adquirido en corriente
        self.sensitivities = esp_med_par.get_sensitivities()
        # Offset de los amplificadores
        self.offsets = esp_med_par.get_offsets()
        # Indice de los canales DC
        self.dc_idx = list(range(1, 3 * self.n_det, 3))
        if self.cip: self.dc_idx.append(self.n_det*3)
        # Indice de los canales AC entrada filtro antialiasing
        self.ac_idx = list(range(2, 3 * self.n_det, 3))

        # Se admite al 1% de los datos saturados para cada canal
        self.max_range_sat = 0.01 * self.pts_hist * self.tot_hist
        # Se admite al 1% de los datos saturados a la entrada del Anti-Aliasing
        self.max_ac_sat = 0.01 * self.pts_hist * self.tot_hist

        # Para guardar cada nueva historia
        self._new_history = []
        # Contador de historias adquiridas
        self.num_histories = 0
        # Registra datos saturados en cada canal
        # usa coefs para saber cuántas señales se adquieren
        self.saturation_range = np.zeros(len(self.coefs))
        # Registra datos saturados en la entrada del anti-aliasing
        # Es uno por cada cadena utilizada
        self.saturation_ac_filt = np.zeros(self.n_det)

        self.reference_volt = []

        self.init_ui()

        self.COLOR_FUENTE = self.palette().windowText().color().name()

    def init_ui(self):
        self.layout = QGridLayout()
        # Barra de progreso
        self.pbar = QProgressBar(self, minimum=0, maximum=self.tot_hist,
                                 value=0)
        self.layout.addWidget(self.pbar, 0, 0, 1, 4)
        # Labels para cada fila
        labels_fil = { "V [V]": (2, 0),
                       "Vo [V]": (3, 0),
                       "I [A]": (4,0),
                      }
        # Labels para cada columna
        labels_col = {self.labels[3*i+1]: (1, i+1) for i in range(self.n_det)}
        if self.cip:
            labels_col[self.labels[-1]] = (1, self.n_det + 1)
        labels = {**labels_fil, **labels_col}
        # Se general los labels para cada fila y columnas
        self.labels = {}
        for labtext, pos in labels.items():
            self.labels[labtext] = QLabel(labtext)
            self.labels[labtext].setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.layout.addWidget(self.labels[labtext], pos[0], pos[1])

        # Display para los números
        _det_tot = self.n_det + 1 if self.cip else self.n_det
        self.lcds = {f"{i}, {j}": (i, j)
                        for i in range(3) for j in range(_det_tot)}
        for key, pos in self.lcds.items():
            self.lcds[key] = QLabel()
            self.lcds[key].setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.layout.addWidget(self.lcds[key], pos[0] + 2, pos[1] + 1)
            self.lcds[key].setStyleSheet("font-weight: bold")
        self.setLayout(self.layout)


    def update_background_parameters(self, sensitivities, offsets):
        """ Parche para pasar parámetros durante medicioń de fondo """
        self.sensitivities = sensitivities
        self.offsets = offsets


    def new_history(self, data):
        # Cuenta la cantida de historias
        self.num_histories += 1
        # Historia adquirida
        self._new_history = data
        # Convierte la lectura de enteros en voltaje
        self._new_history_volts = int_to_volt(self._new_history, self.coefs)
        # Comprueba saturación en el rango de los canales
        self.check_saturation_ranges(self._new_history)
        # Comprueba saturación a la entrada del anti-aliasing
        if self.tipo_med != "Fondo":
            # Sólo si no se está midiendo fondo
            self.check_saturation_antialiasing(
                                self._new_history_volts[self.ac_idx, :])
        # Emite la señal con los datos para ser graficada
        self.data_in_volts.emit(self._new_history_volts)
        # Se muestran los valores medios de las DC
        # Datos en volts
        dc_data = self._new_history_volts[self.dc_idx, :]
        volt_texts = []
        corr_texts = []
        for i, ch in enumerate(dc_data):
            volt_text = "{:.4f}".format(np.mean(ch))
            volt_texts.append(volt_text)
            # Convierto el voltaje promedio a corriente para visualizar
            I_mean = (np.mean(ch) - self.offsets[i]) * self.sensitivities[i]
            curr_text = "{:.3e}".format(I_mean)
            corr_texts.append(curr_text)
            self.layout.itemAtPosition(2, i +1).widget().setText(volt_text)
            self.layout.itemAtPosition(4, i +1).widget().setText(curr_text)
            # Uso la primera historia adquirida como referencia
            # TODO: Conviene utilizar promedio de las primeras ¿3?
            if self.num_histories == 1:
                self.layout.itemAtPosition(3, i +1).widget().setText(volt_text)
                self.reference_volt.append(float(volt_text))
            else:
                # Límites para variaciones del 1% en las corrientes
                # Se debe tener en cuenta el offset de la señal
                sup_li = 1.01 * self.reference_volt[i] - 0.01 * self.offsets[i]
                inf_li = 0.99 * self.reference_volt[i] + 0.01 * self.offsets[i]
                if float(volt_text) >= sup_li:
                    self.layout.itemAtPosition(2, i +1).widget().setStyleSheet(
                                               "color: red; font-weight: bold")
                    self.layout.itemAtPosition(4, i +1).widget().setStyleSheet(
                                               "color: red; font-weight: bold")
                elif float(volt_text) <= inf_li:
                    self.layout.itemAtPosition(2, i +1).widget().setStyleSheet(
                                              "color: blue; font-weight: bold")
                    self.layout.itemAtPosition(4, i +1).widget().setStyleSheet(
                                              "color: blue; font-weight: bold")
                else:
                    self.layout.itemAtPosition(2, i +1).widget().setStyleSheet(
                              f"color:{self.COLOR_FUENTE} ; font-weight: bold")
                    self.layout.itemAtPosition(4, i +1).widget().setStyleSheet(
                              f"color:{self.COLOR_FUENTE} ; font-weight: bold")

        self.pbar.setValue(self.num_histories)
        print("num_histories", self.num_histories)
        if self.num_histories == self.tot_hist:
            self.all_histories_read.emit()
        self.valores_control.emit(self.num_histories, volt_texts, corr_texts)
        return None


    def check_saturation_ranges(self, incoming_data):
        """ Comprueba si se produce saturación en el rango de la DAC usado """
        # Cuenta la cantida de datos saturados
        self.saturation_range += np.count_nonzero(
                                   incoming_data==self.SATURATION_BIT, axis=1)
        print(f"**** Datos rangos saturados: {self.saturation_range}")
        # Determina qué canal está saturado
        sat_channels_range = np.where(
                                self.saturation_range > self.max_range_sat)[0]
        if len(sat_channels_range) != 0:
            if self.tipo_med != "Fondo":
                self.data_saturation.emit("Rango", list(sat_channels_range))
                print(f"**** Saturación en los canales {sat_channels_range}")
            else:
                # Si se está midiendo fondo, sólo se corta la adquisición en
                # caso de estar saturando los canales DC
                dc_saturados = []
                for dc in self.dc_idx:
                    if dc in sat_channels_range:
                        dc_saturados.append(dc)
                if dc_saturados:
                    self.data_saturation.emit("Rango", dc_saturados)
        return None


    def check_saturation_antialiasing(self, ac_data):
        # Cuenta la cantida de datos saturados
        self.saturation_ac_filt += np.count_nonzero(
                                ac_data > self.SATURATION_AC_ANTIALIAS, axis=1)
        print(f"**** Datos saturados entrada AA: {self.saturation_ac_filt}")
        # Determina qué canal está saturado
        sat_channels_ac = np.where(
                               self.saturation_ac_filt > self.max_ac_sat)[0]
        if len(sat_channels_ac) != 0:
            # Corta la medición sólo si no se está midiendo fondo
            if self.tipo_med != "Fondo":
                # Vuelvo a los índices reales de todas las señales
                true_indx = np.array([2 + 3 * i for i in sat_channels_ac],
                                      dtype=int)
                if DEBUG_MODE:
                    print(80*"*" + "\n\n")
                    print("OJO: NO SE EMITE SEÑAL SI HAY SATURACION",
                          "EN FILTRO (SE TRABAJA EN MODO DEBUG)")
                    print("\n\n" + 80*"*")
                else:
                    self.data_saturation.emit("AC_AA", list(true_indx))
                print(f"**** Saturación en el filtro AA {true_indx}")
        return None


class VentanaControlDC(QMainWindow):
    """
    Ventana para mostrar en grande los valores de DC durante la adquisición

    Sirve para visualizar fácilmente y tomar decisiones en la estabilización
    del reactor
    """
    # Señal para indicar que se ceró la ventana
    control_win_closed = pyqtSignal()


    def __init__(self, tot_hist, n_det, labels, cip, offsets):
        super().__init__()

        self.tot_hist = tot_hist
        self.n_det = n_det
        self.labels = labels
        self.cip = cip
        self.offsets = offsets

        self.reference_volt = []
        self.init_ui()

        self.COLOR_FUENTE = self.palette().windowText().color().name()

    def init_ui(self):
        """
        ES una copia de ProgresoMedicion()
        """

        self.setWindowTitle("Control")
        self.resize(QSize(900, 300))
        self.center()
        # Tamaño fuente para todos los QLabels de esta ventana
        self.setStyleSheet("QLabel{font-size: 20pt;}")

        self.layout = QGridLayout()
        # Barra de progreso
        self.pbar = QProgressBar(self, minimum=0, maximum=self.tot_hist,
                                 value=0)
        self.layout.addWidget(self.pbar, 0, 0, 1, 4)
        # Labels para cada fila
        labels_fil = { "V [V]": (2, 0),
                       "Vo [V]": (3, 0),
                       "I [A]": (4,0),
                      }
        # Labels para cada columna
        labels_col = {self.labels[3*i+1]: (1, i+1) for i in range(self.n_det)}
        if self.cip:
            labels_col[self.labels[-1]] = (1, self.n_det + 1)
        labels = {**labels_fil, **labels_col}
        # Se general los labels para cada fila y columnas
        self.labels = {}
        for labtext, pos in labels.items():
            self.labels[labtext] = QLabel(labtext)
            self.labels[labtext].setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.layout.addWidget(self.labels[labtext], pos[0], pos[1])
            # self.labels[labtext].setStyleSheet("font-weight: bold;")

        # Display para los números
        _det_tot = self.n_det + 1 if self.cip else self.n_det
        self.lcds = {f"{i}, {j}": (i, j)
                        for i in range(3) for j in range(_det_tot)}
        for key, pos in self.lcds.items():
            self.lcds[key] = QLabel()
            self.lcds[key].setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.layout.addWidget(self.lcds[key], pos[0] + 2, pos[1] + 1)
            self.lcds[key].setStyleSheet("font-weight: bold;")
        self.setLayout(self.layout)

        self.mainbox = QWidget(self)
        self.mainbox.setLayout(self.layout)
        self.setCentralWidget(self.mainbox)


    def center(self):
        """ Center window on screen """
        qr = self.frameGeometry()
        cp = QtGui.QGuiApplication.primaryScreen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())


    @pyqtSlot(int, list, list)
    def _update_data(self, num_hist, volts, corrientes):
        for i, (volt, corr) in enumerate(zip(volts, corrientes)):
            self.layout.itemAtPosition(2, i +1).widget().setText(volt)
            self.layout.itemAtPosition(4, i +1).widget().setText(corr)
            # Uso la primera historia adquirida como referencia
            if num_hist == 1:
                self.layout.itemAtPosition(3, i +1).widget().setText(volt)
                self.reference_volt.append(float(volt))
            else:
                # Límites para variaciones del 1% en las corrientes
                # Se debe tener en cuenta el offset de la señal
                sup_li = 1.01 * self.reference_volt[i] - 0.01 * self.offsets[i]
                inf_li = 0.99 * self.reference_volt[i] + 0.01 * self.offsets[i]
                if float(volt) >= sup_li:
                    self.layout.itemAtPosition(2, i +1).widget().setStyleSheet(
                                               "color: red; font-weight: bold")
                    self.layout.itemAtPosition(4, i +1).widget().setStyleSheet(
                                               "color: red; font-weight: bold")
                elif float(volt) <= inf_li:
                    self.layout.itemAtPosition(2, i +1).widget().setStyleSheet(
                                              "color: blue; font-weight: bold")
                    self.layout.itemAtPosition(4, i +1).widget().setStyleSheet(
                                              "color: blue; font-weight: bold")
                else:
                    self.layout.itemAtPosition(2, i +1).widget().setStyleSheet(
                              f"color:{self.COLOR_FUENTE} ; font-weight: bold")
                    self.layout.itemAtPosition(4, i +1).widget().setStyleSheet(
                              f"color:{self.COLOR_FUENTE} ; font-weight: bold")
        self.pbar.setValue(num_hist)


    def closeEvent(self, event):
        self.control_win_closed.emit()
        event.accept()


if __name__ == "__main__":
    pass
