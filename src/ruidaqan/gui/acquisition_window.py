import sys
import os
import numpy as np
from PyQt6 import QtGui
from PyQt6.QtCore import QSize, pyqtSignal, pyqtSlot, QTimer, Qt
from PyQt6.QtWidgets import (QMessageBox, QGridLayout, QLabel, QPushButton,
                             QProgressBar, QTabWidget, QWidget, QVBoxLayout,
                             QHBoxLayout, QLayout, QGroupBox, QMenuBar, QMenu,
                             QStatusBar, QMainWindow, QToolBar)
# --- From DAQ Control --- #
from .parameters import GeneralParamTree, AdvancedParamTree, EspMedParamTree
from .plotter import TabsPlot
from .procesado_gui import (ProgresoMedicion, ShowRangesUtilization,
                           VentanaControlDC)
from .data_io import (write_RUI_file, write_RUI_background, write_background,
                     WriteHDF5File)
from .cip import InputIpValues
from .procesamiento_window import FitWindow
from .ventanas_ayuda import VentanaAyuda
import ruidaqan
if ruidaqan.DEBUG_MODE:
    from .reader_debug import SignalReader, GetDevicesInfo
else:
    from .reader import SignalReader, GetDevicesInfo


class RangeAdjustmentWindow(QMainWindow):
    """
    TODO
    """

    rangeadj_win_closed = pyqtSignal()
    rangeadj_adjusted = pyqtSignal(list)


    def __init__(self, tipo_med=None):
        super().__init__()

        self.tipo_med = tipo_med

        self.SAMPLE_RATE = 2 * 200.0
        self.SAMPLE_SIZE = 512
        self.TOT_HISTORIAS = 2

        self.cfg_gral = GeneralParamTree(reset=False)
        self.n_det = self.cfg_gral.get_param_value("Parámetros generales",
                                                   "Cadenas de medición")
        self.cip = self.cfg_gral.get_param_value("Parámetros generales",
                                                 "Medición de CIp")

        # Se cargan configuraciones avanzadas
        self.cfg_adv = AdvancedParamTree(self.n_det, self.cip, reset=False)
        self.labels = self.cfg_adv.get_channels_labels()
        # Canales
        self.channels = self.cfg_adv.get_channels()
        # Rangos disponibles en el dispositivo
        self.available_rngs_bi = self.cfg_adv.get_ADC_ranges()

        self.show_ranges = ShowRangesUtilization(self.cfg_adv)

        # Los rangos son bipolares, pero como se trabaja con señales unipolares
        # creo un diccionario para facilitar la notación
        self.dic_rng = {it[1]:it for it in self.available_rngs_bi}
        # Rangos unipolares
        self.available_rngs = list(self.dic_rng.keys())
        # Se comienza con el rango más alto
        # [AC, DC, AC_filt, ... , DC_CIP]
        # TODO: no hardcodear rangos
        self.max_rngs_bi = self.n_det * [(-5.0, 5.0), (-10.0, 10.0), (-5.0, 5.0)]
        if self.cip: self.max_rngs_bi.append((-10.0, 10.0))
        # Rangos máximos unipolares
        self.max_rngs = [it[1] for it in self.max_rngs_bi]
        # Rangos acutales bipolares
        self.cur_ranges_bi = self.cfg_adv.get_channels_ranges()
        # Rangos acutales unipolares
        self.cur_ranges = [r[1] for r in self.cur_ranges_bi]

        # Se cargan configuraciones de la medición
        self.cfg_meas = EspMedParamTree(self.n_det, self.cip, reset=True)
        # Sensibilidades del amplificador
        self.sensitivities = self.cfg_meas.get_sensitivities()
        # Offset de los amplificadores
        self.offsets = self.cfg_meas.get_offsets()

        self.valid = ProgresoMedicion(
                              self.cfg_meas,
                              self.cfg_adv,
                              tipo_med=self.tipo_med,
                              par_fondo=(self.SAMPLE_RATE, self.SAMPLE_SIZE,
                                         self.TOT_HISTORIAS)
                              )

        self.init_ui()
        self._createMenu()
        self.init_daq_io()

        # Para acumular datos en volts
        self.historias_acumuladas = []
        self.valid.data_in_volts.connect(self.acumula_historias_volt)

        # Se pasan los datos leidos para validar
        self.read_thread.incoming_data.connect(self.valid.new_history)
        # Acción para cuando se interrumpe la adquisicón por saturación
        self.valid.data_saturation.connect(self.data_saturated)

        self.monitor_btn.clicked.connect(self.start_monitoring)
        self.adjust_btn.clicked.connect(self.start_adjusting)

        self.accept_cur_btn.clicked.connect(self.accept_cur_clicked)
        self.accept_adj_btn.clicked.connect(self.accept_adj_clicked)
        self.cancel_btn.clicked.connect(self.cancel_btn_clicked)
        # Comienza ajustando rangos apenas se abre
        self.start_adjusting()


    def init_ui(self):
        self.resize(300, 300)
        self.setWindowTitle("Ajuste de rangos")
        self.center()

        layout = QVBoxLayout()

        self.start_signal_btn = QPushButton("Ajustar rangos")
        self.monitor_btn = QPushButton("Monitorear")
        self.adjust_btn = QPushButton("Ajustar")
        layout_acq = QHBoxLayout()
        layout_acq.addWidget(self.monitor_btn)
        layout_acq.addWidget(self.adjust_btn)

        self.groupBox_btns = QGroupBox("Continuar con rangos:")
        layout_btns = QHBoxLayout(self.groupBox_btns)
        self.accept_cur_btn = QPushButton(self.groupBox_btns)
        self.accept_cur_btn.setText("Actuales")
        self.accept_adj_btn = QPushButton(self.groupBox_btns)
        self.accept_adj_btn.setText("Ajustados")
        self.cancel_btn = QPushButton(self.groupBox_btns)
        self.cancel_btn.setText("Cancelar")
        self.accept_adj_btn.setEnabled(False)

        layout_btns.addWidget(self.accept_cur_btn)
        layout_btns.addWidget(self.accept_adj_btn)
        layout_btns.addWidget(self.cancel_btn)

        layout.addWidget(self.show_ranges)
        layout.addLayout(layout_acq)
        layout.addWidget(self.groupBox_btns)

        self.mainbox = QWidget(self)
        self.mainbox.setLayout(layout)
        self.setCentralWidget(self.mainbox)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)


    def _createMenu(self):
        menu1 = self.menuBar()
        # menu1.addMenu('File')

        self.menu_bar = QMenuBar(menu1)
        menu1.setCornerWidget(self.menu_bar, Qt.Corner.TopRightCorner)
        self.menu_derecho  = QMenu(self.menu_bar)
        self.ayuda = self.menu_bar.addMenu("&Ayuda")
        self.ayuda.addAction('Ayuda ventana', self.show_ayuda_win)


    @pyqtSlot()
    def show_ayuda_win(self):
        self.ayuda_win = VentanaAyuda(referencia="ajuste-de-rangos")
        self.ayuda_win.show()


    def center(self):
        """ Center window on screen """
        qr = self.frameGeometry()
        cp = QtGui.QGuiApplication.primaryScreen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())


    def init_daq_io(self):
        # initiate read threads for analog input
        self.read_thread = SignalReader(
                sample_rate=self.SAMPLE_RATE,
                sample_size=self.SAMPLE_SIZE,
                #channels=self.cfg_adv.get_channels(),
                channels=self.channels,
                ranges=self.cfg_adv.get_channels_ranges(),
                reading_type="int16",
                terminal_cfg="RSE",
        )


    @pyqtSlot()
    def start_monitoring(self):
        self.historias_acumuladas = []
        self.status_bar.showMessage("Monitoreando con rangos actuales...")
        self.read_thread.input_ranges = self.cur_ranges_bi
        self.read_thread.is_running = True
        self.read_thread.start()
        # Desconecto y conecto los slots
        try:
            self.valid.all_histories_read.disconnect()
        except TypeError: pass
        self.valid.all_histories_read.connect(self._monitoring_finished)
        self.groupBox_btns.setEnabled(False)
        self.monitor_btn.setEnabled(False)
        self.adjust_btn.setEnabled(False)


    @pyqtSlot()
    def _monitoring_finished(self):
        self._closing_acquisition()
        all_data = np.hstack(self.historias_acumuladas)
        # Calculo utilización y muestro
        porcentaje_utilizado = \
                np.max(all_data, axis=1) / self.cur_ranges * 100
        self.show_ranges.update(self.cur_ranges_bi, porcentaje_utilizado)

        if not hasattr(self , "adj_ranges_bi"):
            self.accept_adj_btn.setEnabled(False)


    @pyqtSlot()
    def start_adjusting(self):
        self.historias_acumuladas = []
        self.status_bar.showMessage("Ajustando rangos...")
        # Aplico rangos máximos para la adquisición
        self.read_thread.input_ranges = self.max_rngs_bi
        self.cfg_adv.set_channels_ranges(self.max_rngs_bi)

        self.valid.coefs = self.cfg_adv.get_channels_coefs(
                                               self.channels, self.max_rngs_bi)

        self.read_thread.is_running = True
        self.read_thread.start()
        # Desconecto y conecto los slots
        try:
            self.valid.all_histories_read.disconnect()
        except TypeError: pass
        self.valid.all_histories_read.connect(self._adjusting_finished)

        self.groupBox_btns.setEnabled(False)
        self.monitor_btn.setEnabled(False)
        self.adjust_btn.setEnabled(False)


    @pyqtSlot()
    def _adjusting_finished(self):
       self._closing_acquisition()
       all_data = np.hstack(self.historias_acumuladas)
       self.select_ranges(all_data)
       self.accept_adj_btn.setEnabled(True)


    def _closing_acquisition(self):
        self.read_thread.is_running = False
        self.read_thread.wait()

        self.groupBox_btns.setEnabled(True)
        self.monitor_btn.setEnabled(True)
        self.adjust_btn.setEnabled(True)
        self.status_bar.showMessage("")

        self.valid.num_histories = 0


    def select_ranges(self, data):
        """
        Métdoo donde se elije el rango

        No va a funcionar bien cuando se trabaje con datos simulados porque los
        coeficientes de calibración no generan los voltajes reales.

        Se ajusta el rango trabajando en voltaje, es más conservativo que
        trabajar con los int16 (en general la tarjeta satura apenas por encima
        del valor máximo del rango)
        """
        # Valores máximos adquiridos en cada canal (de los valores absolutos)
        max_values = np.max(abs(data), axis=1)
        # Se comienza con los valores máximos (unipolares)
        adj_ranges = self.max_rngs
        _av_rng = np.asarray(self.available_rngs)
        for i, max_val in enumerate(max_values):
            if (i + 1) % 3 != 0:
                # Los rangos de AC_filt quedan fijos 
                try:
                    # Primer rango mayor al máximo valor medido
                    adj_ranges[i] = _av_rng[_av_rng > max_val][0]
                except IndexError:
                    print(f"Canal {self.labels[i]} saturado,",
                          "nunca se debió llegar hasta acá")
        # Vuelvo a notación correcta de rangos, (-r, r)
        self.adj_ranges_bi = [self.dic_rng[r] for r in adj_ranges]
        # Aplico los rangos
        self.cfg_adv.set_channels_ranges(self.adj_ranges_bi)
        # print(f"Rangos ajustados: {adj_ranges}")
        porcentaje_utilizado = max_values / np.asarray(self.max_rngs) * 100
        # print(f"Utilización del rango: {porcentaje_utilizado} %")
        self.show_ranges.update(self.adj_ranges_bi, porcentaje_utilizado)


    @pyqtSlot()
    def accept_cur_clicked(self):
        self.cfg_adv.set_channels_ranges(self.cur_ranges_bi)
        self.cfg_adv.save_settings()
        self.rangeadj_adjusted.emit(self.cur_ranges_bi)
        self.close()


    @pyqtSlot()
    def accept_adj_clicked(self):
        self.cfg_adv.set_channels_ranges(self.adj_ranges_bi)
        self.cfg_adv.save_settings()
        self.rangeadj_adjusted.emit(self.adj_ranges_bi)
        self.close()


    @pyqtSlot()
    def cancel_btn_clicked(self):
        self.close()


    @pyqtSlot(np.ndarray)
    def acumula_historias_volt(self, new_data):
        """ Acumula datos para luego promediar """
        self.historias_acumuladas.append(new_data)


    @pyqtSlot(str, list)
    def data_saturated(self, tipo, canales):
        """ Finaliza la adquisicón una vez completadas todas las historias"""
        self.read_thread.is_running = False
        self.read_thread.wait()
        self.rangeadj_win_closed.emit()
        self.close()

        msg = QMessageBox()
        msg.setWindowTitle("Medición fallida")
        if tipo == "AC_AA":
            # Saturación a la entrada del filtro antialiasing
            msg.setText("Saturación en el filtro anti-aliasing")
        elif tipo == "Rango":
            # Saturacion en rango de la DAQ
            msg.setText("Saturación en el rango de la tarjeta")
        _info = "Más del 1% de los datos están saturados\n\n"
        _info += "Los canales saturados fueron:\n\t"
        for canal in canales:
            _info += self.labels[canal] + "  "
        msg.setDetailedText(_info)
        msg.setDetailedText(_info)
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.exec()


    def closeEvent(self, event):
        if self.read_thread.is_running:
            self.read_thread.is_running = False
            self.read_thread.wait()
        self.rangeadj_win_closed.emit()


class BackgroundWindow(QMainWindow):
    """
    Window for background measurement
    """
    background_win_closed = pyqtSignal()


    def __init__(self, data_folder):
        super().__init__()

        # Constantes para medir fondo
        self.SAMPLE_RATE = 2 * 200.0
        self.SAMPLE_SIZE = 512
        self.TOT_HISTORIAS = 100

        # Carpeta para guardar datos
        self.DATA_FOLDER = data_folder

        # Para controlar el estado del botón de comienzo de medición
        self._ajustados = False

        self.cfg_gral = GeneralParamTree(reset=False)
        self.n_det = self.cfg_gral.get_param_value("Parámetros generales",
                                                   "Cadenas de medición")
        self.cip = self.cfg_gral.get_param_value("Parámetros generales",
                                                 "Medición de CIp")
        self.serie = self.cfg_gral.get_param_value("Parámetros generales",
                                                   "Serie")
        # Se cargan configuraciones avanzadas
        self.cfg_adv = AdvancedParamTree(self.n_det, self.cip, reset=False)
        # Labels de los canales
        self.labels = self.cfg_adv.get_channels_labels()
        # Canales
        self.channels = self.cfg_adv.get_channels()
        # Se cargan configuraciones de la medición
        self.cfg_meas = EspMedParamTree(self.n_det, self.cip, reset=True)
        # Se ocultan parámetros Medición
        self.cfg_meas.params.param("Parámetros medición", "Medición").remove()
        # Se ocultan parámetros DAQ (¿o conviene dejarlo para cambiar?)
        self.cfg_meas.params.param("Parámetros medición", "DAQ").remove()
        # Se oculan ganancias de AC
        self.cfg_meas.hide_AC_gains()

        self.valid = ProgresoMedicion(
                              self.cfg_meas,
                              self.cfg_adv,
                              tipo_med="Fondo",
                              par_fondo=(self.SAMPLE_RATE, self.SAMPLE_SIZE,
                                         self.TOT_HISTORIAS)
                              )

        self.init_ui()
        self._createMenu()

        # Para acumular datos en volts
        self.historias_acumuladas = []
        self.valid.data_in_volts.connect(self.acumula_historias_volt)

        # Acción para cuando se adquieren todas las historias pedidas 
        self.valid.all_histories_read.connect(self.finished_all_histories)
        # Acción para cuando se interrumpe la adquisicón por saturación
        self.valid.data_saturation.connect(self.data_saturated)
        # Ventana ajuste de rangos
        self.rangeadj_win_exist = False
        self.btn_rangos.clicked.connect(self.show_rangeadj_win)


    def init_ui(self):
        self.resize(350, 600)
        self.setWindowTitle("Medición del fondo")
        self.center()

        layout = QVBoxLayout()

        self.btn_rangos = QPushButton("Comenzar medición")

        layout.addWidget(self.cfg_meas)
        layout.addWidget(self.valid)
        layout.addWidget(self.btn_rangos)

        self.mainbox = QWidget(self)
        self.mainbox.setLayout(layout)
        self.setCentralWidget(self.mainbox)


    def center(self):
        """ Center window on screen """
        qr = self.frameGeometry()
        cp = QtGui.QGuiApplication.primaryScreen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())


    def init_daq_io(self):
        # initiate read threads for analog input
        self.read_thread = SignalReader(
                sample_rate=self.SAMPLE_RATE,
                sample_size=self.SAMPLE_SIZE,
                channels=self.cfg_adv.get_channels(),
                ranges=self.cfg_adv.get_channels_ranges(),
                reading_type="int16",
                terminal_cfg="RSE",
        )


    def _createMenu(self):
        menu1 = self.menuBar()
        # menu1.addMenu('File')

        self.menu_bar = QMenuBar(menu1)
        menu1.setCornerWidget(self.menu_bar, Qt.Corner.TopRightCorner)
        self.menu_derecho  = QMenu(self.menu_bar)
        self.ayuda = self.menu_bar.addMenu("&Ayuda")
        self.ayuda.addAction('Ayuda ventana', self.show_ayuda_win)


    @pyqtSlot()
    def show_ayuda_win(self):
        self.ayuda_win = VentanaAyuda(referencia="medicion-de-fondo")
        self.ayuda_win.show()


    @pyqtSlot()
    def show_rangeadj_win(self):
        if not self.rangeadj_win_exist:
            self.btn_rangos.setEnabled(False)
            self.rangeadj_win = RangeAdjustmentWindow("Fondo")
            self.rangeadj_win_exist = True
            self.rangeadj_win.show()
            self.rangeadj_win.rangeadj_win_closed.connect(
                                                    self.close_rangeadj_win)
            self.rangeadj_win.rangeadj_adjusted.connect(self.range_adjusted)
        else:
            self.rangeadj_win.close()


    @pyqtSlot(list)
    def range_adjusted(self, new_ranges):
        self._ajustados = True
        # Se aplican los nuevo rango
        self.cfg_adv.set_channels_ranges(new_ranges)
        # Se instancia la clase de adquisicón
        self.init_daq_io()
        # Se pasan los datos leidos para validar
        self.read_thread.incoming_data.connect(self.valid.new_history)

        # Actualizo los coeficientes que cambian con los nuevos rangos
        self.valid.coefs = self.cfg_adv.get_channels_coefs(
                                                    self.channels, new_ranges)

        # Una vez que se ajustan los rangos, se comienza la medición
        # Sensibilidades del amplificador
        self.sensitivities = self.cfg_meas.get_sensitivities()
        # Offset de los amplificadores
        self.offsets = self.cfg_meas.get_offsets()
        # Se pasan las sensibilidades y offsets para ver corrientes on-line
        self.valid.update_background_parameters(self.sensitivities,
                                                self.offsets)
        self.start_signal_btn_click()


    @pyqtSlot()
    def close_rangeadj_win(self):
        self.rangeadj_win_exist = False
        if not self._ajustados:
            self.btn_rangos.setEnabled(True)


    @pyqtSlot()
    def start_signal_btn_click(self):
        """ Start and Stop the data acquisition """
        if self.read_thread.is_running:
            print("Finaliza medición de fondo")
            self.read_thread.is_running = False
            self.read_thread.wait()
        else:
            print("Comienza medición de fondo")
            self.read_thread.start()


    @pyqtSlot(np.ndarray)
    def acumula_historias_volt(self, new_data):
        """ Acumula datos para luego promediar """
        self.historias_acumuladas.append(new_data)


    @pyqtSlot(str, list)
    def data_saturated(self, tipo, canales):
        """ Finaliza la adquisicón una vez completadas todas las historias"""
        self.read_thread.is_running = False
        self.read_thread.wait()
        self.background_win_closed.emit()
        self.close()

        msg = QMessageBox()
        msg.setWindowTitle("Medición fallida")
        if tipo == "AC_AA":
            # Saturación a la entrada del filtro antialiasing
            msg.setText("Saturación en el filtro anti-aliasing")
        elif tipo == "Rango":
            # Saturacion en rango de la DAQ
            msg.setText("Saturación en el rango de la tarjeta")
        _info = "Más del 1% de los datos están saturados\n\n"
        _info += "Los canales saturados fueron:\n\t"
        for canal in canales:
            _info += self.labels[canal] + "  "
        msg.setDetailedText(_info)
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.exec()


    @pyqtSlot()
    def finished_all_histories(self):
        """ Finaliza la adquisicón una vez completadas todas las historias"""
        self.read_thread.is_running = False
        self.read_thread.wait()
        self.background_win_closed.emit()

        # Se escriben los datos en formato .RUI
        all_data = np.hstack(self.historias_acumuladas)
        # Indice de los canales DC
        # dc_idx = list(range(self.n_det, 2 * self.n_det))
        dc_idx = list(range(1, 3 * self.n_det, 3))
        if self.cip: dc_idx.append(self.n_det*3)
        # Obtendo las corrientes
        mean_dc_data = []
        std_dc_data = []
        for k, ind in enumerate(dc_idx):
            # Promedios voltajes sin offset
            mean_volts = np.mean(all_data[ind, :]) - self.offsets[k]
            # Promedios corrientes
            mean_dc_data.append(mean_volts * self.sensitivities[k])
            # Desvio voltajes sin offset
            std_volts = np.std(all_data[ind, :] - self.offsets[k], ddof=1)
            # Desvío corrienets
            std_dc_data.append(std_volts * self.sensitivities[k])
        # Nombre de los archivos de fondo para FERCIN3
        names_RUI = [f"FONDO{i+1}" for i in range(self.n_det)]
        if self.cip: names_RUI.append("FONDO-IP")
        # Agrego la carpeta en donde se guardarán
        names_path = [os.path.join(self.DATA_FOLDER, s) for s in names_RUI]
        # Graba en formato FERCIN3
        write_RUI_background(names_path, mean_dc_data, std_dc_data)
        # Graba nuevo formato
        filename = f"S{self.serie:03d}-FONDOS"
        file_path = os.path.join(self.DATA_FOLDER, filename)
        write_background(file_path, mean_dc_data, std_dc_data)

        self.close()

        msg = QMessageBox()
        msg.setWindowTitle("Información")
        msg.setText("Medición de fondo finalizada de forma exitosa")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.exec()


    def closeEvent(self, event):
        if self.rangeadj_win_exist:
            self.rangeadj_win.close()
        try:
            if self.read_thread.is_running:
                self.read_thread.is_running = False
                self.read_thread.wait()
        except AttributeError:
            pass
        self.background_win_closed.emit()


class AcquisitionWindow(QMainWindow):

    # Señal para indicar que se cierra esta ventana
    acq_win_closed = pyqtSignal()

    def __init__(self, output_file_HDF):
        super().__init__()

        # Nombre del archivo de salida en formato .RUI
        self.output_file_HDF = output_file_HDF

        # Se cargan configuraciones generales
        self.cfg_gral = GeneralParamTree(reset=False)
        self.cfg_gral.set_whole_tree("readonly")
        self.n_det = self.cfg_gral.get_param_value(
                             "Parámetros generales", "Cadenas de medición")
        self.cip = self.cfg_gral.get_param_value(
                             "Parámetros generales", "Medición de CIp")
        # Se cargan configuraciones avanzadas
        self.cfg_adv = AdvancedParamTree(self.n_det, self.cip, reset=False)
        self.cfg_adv.set_whole_tree("readonly")
        self.res_ADC = self.cfg_adv.get_ADC_resolution()
        # Labels de los canales
        self.labels = self.cfg_adv.get_channels_labels()
        # Se cargan configuraciones de la medición
        self.cfg_meas = EspMedParamTree(self.n_det, self.cip, reset=False)
        self.offsets = self.cfg_meas.get_offsets()
        self.cfg_meas.set_whole_tree("readonly")
        self.tot_hist = self.cfg_meas.get_param_value("Parámetros medición",
                                                      "DAQ", "Historias")

        # Instancia para validar cada historia adquirida
        self.valid = ProgresoMedicion(
                                      self.cfg_meas,
                                      self.cfg_adv,
                                      )
        # Instancia para visualizar utilización de rangos
        self.show_ranges = ShowRangesUtilization(self.cfg_adv)

        # Instancia para grabar datos en formato HDF
        self.writer_hdf = WriteHDF5File(self.output_file_HDF,self.cfg_gral,
                                        self.cfg_adv, self.cfg_meas)

        self.init_ui()
        self.init_daq_io()
        if not self.cip: self.init_cip_win()

        # Flag para saber si terminó la adquisición
        self.acq_finished = False
        # Variable para los valores manuales de Ip
        self.cip_data = None

        # Para la ventana de control DC
        self.control_win = VentanaControlDC(self.tot_hist, self.n_det,
                self.labels, self.cip, self.offsets)
        self.control_win_exist = False
        # Para el cierre
        self.control_win.control_win_closed.connect(self._close_control_grande)
        # Para pasar los datos de ProgresoMedición() a la ventana de control
        self.valid.valores_control.connect(self.control_win._update_data)

        # Para acumular datos (transitorio, sólo para escribir .RUI)
        self.historias_acumuladas = []
        self.read_thread.incoming_data.connect(self.acumula_historias)
        # Se pasan los datos leidos para validar
        self.read_thread.incoming_data.connect(self.valid.new_history)
        # Se pasan los datos en Volts para graficar
        self.valid.data_in_volts.connect(self.tabs_plot.update_plots)
        # Acción para cuando se adquieren todas las historias pedidas 
        self.valid.all_histories_read.connect(self.acquisition_finished)
        # Acción para cuando se interrumpe la adquisicón por saturación
        self.valid.data_saturation.connect(self.data_saturated)

        # Comienza la adquisición de forma automática
        self.start_signal_btn_click()


    def init_ui(self):
        """ Define and initialize GUI """
        self.resize(QSize(1170, 750)) # ancho, alto
        self.setWindowTitle("Medición")
        # Esto se hace por un bug que hay en Windows 10
        QTimer.singleShot(1, self.showMaximized)
        self._createToolBar()
        self._createMenu()

        if self.cip: self.center()

        layout = QGridLayout()

        self.tabs_view = QTabWidget()
        self.tabs_view.setMaximumWidth(350)
        self.tabs_view.setTabPosition(QTabWidget.TabPosition.West)
        self.tabs_view.addTab(self.cfg_meas, "Medición")
        self.tabs_view.addTab(self.cfg_gral, "General")
        self.tabs_view.addTab(self.cfg_adv, "Avanzada")
        self.tabs_view.addTab(self.show_ranges, "Rangos")

        self.tabs_plot = TabsPlot(self.cfg_adv, self.cfg_meas)

        left_layout = QVBoxLayout()
        left_layout.addWidget(self.tabs_view)

        center_layout = QVBoxLayout()
        center_layout.addWidget(self.tabs_plot)
        center_layout.addWidget(self.valid)

        main_layout = QHBoxLayout()
        main_layout.addLayout(left_layout)
        main_layout.addLayout(center_layout)

        self.mainbox = QWidget(self)
        self.mainbox.setLayout(main_layout)
        self.setCentralWidget(self.mainbox)


    def center(self):
        """ Center window on screen """
        qr = self.frameGeometry()
        cp = QtGui.QGuiApplication.primaryScreen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())


    def init_daq_io(self):
        # initiate read threads for analog input
        self.read_thread = SignalReader(
                sample_rate=2*self.cfg_meas.get_param_value(
                    "Parámetros medición", "DAQ", "BW manual"), # fs = 2*BW
                sample_size=self.cfg_meas.get_param_value(
                    "Parámetros medición", "DAQ", "Puntos"),
                channels=self.cfg_adv.get_channels(), # Channels
                ranges=self.cfg_adv.get_channels_ranges(),
                reading_type="int16",
                terminal_cfg="RSE",
                max_histories=self.tot_hist,
        )


    def init_cip_win(self):
        self.cip_win_exist = True
        self.cip_win = InputIpValues()
        self.cip_win.show()
        self.cip_win.cip_manual_win_closed.connect(self.cip_finished)


    def _createToolBar(self):
        tools = QToolBar()
        self.addToolBar(tools)
        tools.addAction("Start/Stop", self.start_signal_btn_click)
        tools.addAction("Configuraciones", self._mostrar_configuraciones)
        tools.addAction("Control", self._show_control_grande)
        tools.addAction("Salir", self.close)


    def _mostrar_configuraciones(self):
        if self.tabs_view.isVisible():
            self.tabs_view.hide()
        else:
            self.tabs_view.show()


    def _createMenu(self):
        menu1 = self.menuBar()
        # menu1.addMenu('File')

        self.menu_bar = QMenuBar(menu1)
        menu1.setCornerWidget(self.menu_bar, Qt.Corner.TopRightCorner)
        self.menu_derecho  = QMenu(self.menu_bar)
        self.ayuda = self.menu_bar.addMenu("&Ayuda")
        self.ayuda.addAction('Ayuda ventana', self.show_ayuda_win)


    @pyqtSlot()
    def show_ayuda_win(self):
        self.ayuda_win = VentanaAyuda(referencia="medicion")
        self.ayuda_win.show()


    def _show_control_grande(self):
        if not self.control_win_exist:
            self.control_win_exist = True
            self.control_win.show()
        else:
            self.control_win.close()


    def _close_control_grande(self):
            self.control_win_exist = False


    @pyqtSlot(np.ndarray)
    def acumula_historias(self, new_data):
        # Copio los datos debido a que append guarda referencias de los datos
        cp_data = np.copy(new_data)
        # cuando el thread de adquisición empiece apenas antes de recibir la
        # señal de finalizar la adquisición.
        """ Transitorio, sólo para escribir .RUI """
        self.historias_acumuladas.append(cp_data)
        self.writer_hdf.append_new_data(cp_data)

        # Puebla el widget para visualizar utilización de rangos
        # Notar que acá se controla sobre los int16, y no sobre los
        # voltajes. Habrá una pequeña diferencia respecto a cuando se
        # ajustan los rangos
        max_values = np.max(cp_data, axis=1)
        rngs_bi = self.cfg_adv.get_channels_ranges()
        porcentaje_utilizado = max_values / (2**self.res_ADC / 2 - 1) * 100
        self.show_ranges.update(rngs_bi, porcentaje_utilizado)


    @pyqtSlot(str, list)
    def data_saturated(self, tipo, canales):
        """ Finaliza la adquisicón una vez completadas todas las historias"""
        self.read_thread.is_running = False
        self.read_thread.wait()
        self.acq_win_closed.emit()
        self.close()

        msg = QMessageBox()
        msg.setWindowTitle("Medición fallida")
        if tipo == "AC_AA":
            # Saturación a la entrada del filtro antialiasing
            msg.setText("Saturación en el filtro anti-aliasing")
        elif tipo == "Rango":
            # Saturacion en rango de la DAQ
            msg.setText("Saturación en el rango de la tarjeta")
        _info = "Más del 1% de los datos están saturados\n\n"
        _info += "Los canales saturados fueron:\n\t"
        for canal in canales:
            _info += self.labels[canal] + "  "
        msg.setDetailedText(_info)
        msg.setDetailedText(_info)
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.exec()


    @pyqtSlot(list)
    def cip_finished(self, data):
        self.cip_win_exist = False
        self.cip_data = data
        print(f"Datos en acq_win: {data})")
        if self.acq_finished:
            self.finished_all_histories()


    @pyqtSlot()
    def acquisition_finished(self):
        """ Finaliza la adquisicón una vez completadas todas las historias"""
        self.acq_finished = True
        self.read_thread.is_running = False
        self.read_thread.wait()
        self.acq_win_closed.emit()

        msg = QMessageBox()
        msg.setWindowTitle("Información")
        msg.setText("Adquisición finalizada de forma exitosa")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.exec()

        self.close()

        if self.cip:
            self.finished_all_histories()
        else:
            if not self.cip_win_exist:
                print("Se finaliza medición")
                self.finished_all_histories()
            else:
                print("Se espera finalizar ventana Ip")


    # @pyqtSlot()
    def finished_all_histories(self):
        """
        Finaliza la adquisicón una vez completadas todas las historias y el
        ingreso manual de Ip (si es que no se adquiere)
        """
        # Se escriben valores de Ip ingresado manualmente en HDF5
        if not self.cip:
            self.writer_hdf.append_manual_cip(self.cip_data)

        # Se escriben los datos en formato .RUI

        # Quito un cero al comienzo
        self.output_file_RUI = self.output_file_HDF.replace("S0", "S")
        # Cambio la extensión
        self.output_file_RUI = self.output_file_RUI.replace(".h5", ".RUI")

        all_data = np.hstack(self.historias_acumuladas)
        if self.n_det <= 2:
            write_RUI_file(self.output_file_RUI, all_data, self.cfg_gral,
                        self.cfg_adv, self.cfg_meas, self.cip_data)
            self.fit_window = FitWindow(self.output_file_HDF,
                                                        from_acquisition=True)
            self.fit_window.show()
        else:
            print("No se puede generar archivo .RUI (n_det>2)")


    @pyqtSlot()
    def start_signal_btn_click(self):
        """ Start and Stop the data acquisition """
        if self.read_thread.is_running:
            print("Stopped DAQ acquisition")
            self.read_thread.is_running = False
            self.read_thread.wait()
        else:
            print("Started DAQ acquisition")
            self.read_thread.start()


    def closeEvent(self, event):
        if self.read_thread.is_running:
            self.read_thread.is_running = False
            self.read_thread.wait()
        if self.control_win_exist:
            self.control_win.close()
        self.cfg_adv.set_whole_tree("writable")
        self.acq_win_closed.emit()
        event.accept()


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    if False:
        devices = GetDevicesInfo()
        print(f"Devices in the system {devices.dev_names}")

        for dev in devices.dev_names:
            print(devices.device_info(dev).ai_ranges)
            chan_names = devices.device_info(dev).channel_names
            for chan in chan_names:
                print(chan)
                print(devices.device_info(dev).scaling_coeff(chan, (-10, 10)))
        quit()

    app = QApplication(sys.argv)
    mainWin = AcquisitionWindow("test.RUI")
    mainWin.show()
    ap_ex = app.exec()

    quit()

    # After aqcuisition, plot data
    print("End acquisition")
    import numpy as np
    import matplotlib.pyplot as plt
    data = np.loadtxt("Output_Data.dat")
    fig, ax = plt.subplots(1, 1)
    ax.plot(data)
    ax.set_xlabel("Data points")
    ax.set_ylabel("Voltage [V]")
    ax.set_title("Measured signals")
    plt.show()

    sys.exit(ap_ex)
    #sys.exit(app.exec())
