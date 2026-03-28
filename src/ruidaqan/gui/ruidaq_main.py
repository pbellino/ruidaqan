#! /usr/bin/env python3

"""GUI for the neutron noise measurement program"""

import os
import pickle
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QLabel, QPushButton, QMenu, QMenuBar)
from .parameters import GeneralParamTree, AdvancedParamTree
from .acquisition_window import BackgroundWindow
from .oscilloscope_window import OscilloscopeWindow
from .measurement_window import MeasurementWindow, AdvanceConfigurationWindow
from .appconfig import get_data_folder, ask_data_folder, RESET_DEFAULT_PARAMS
from .ventanas_ayuda import VentanaAyuda, AboutWindow
import ruidaqan
if ruidaqan.DEBUG_MODE:
    from .reader_debug import GetDevicesInfo
else:
    from .reader import GetDevicesInfo


class MainWindow(QMainWindow):
    """Main Window."""

    def __init__(self, parent=None):
        """Initializer."""
        super().__init__(parent)

        self.init_estructura_datos()
        self.init_ui()
        self._create_data_folder()

        self.osc_win_exist = False
        self.btn_osciloscope.clicked.connect(self.show_osc_win)
        self.meas_win_exist = False
        self.btn_measurement.clicked.connect(self.show_meas_win)
        self.advconf_win_exist = False
        self.cfg_gral.paramChange.connect(self.cfg_gral_change)
        self.background_win_exist = False
        self.btn_fondo.clicked.connect(self.show_background_win)


    def init_estructura_datos(self):
        self.cfg_gral = GeneralParamTree(reset=RESET_DEFAULT_PARAMS)
        self.n_det = self.cfg_gral.get_param_value("Parámetros generales",
                                            "Cadenas de medición")
        self.cip = self.cfg_gral.get_param_value("Parámetros generales",
                                            "Medición de CIp")
        self.cfg_adv = AdvancedParamTree(self.n_det, self.cip, reset=True)
        self.cfg_gral.set_whole_tree("writable")


    def init_ui(self):
        self.setGeometry(10, 30, 350, 500)
        self.setWindowTitle('RuiDAQAn')
        self._createMenu()

        self.mainbox = QWidget(self)
        self.setCentralWidget(self.mainbox)
        self.btn_osciloscope = QPushButton("Osciloscopio")
        self.btn_fondo = QPushButton("Medición del fondo")
        self.btn_measurement = QPushButton("Medición")
        self.title = QLabel("Medición de ruido neutrónico")
        self.title.setAlignment(
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.title, 1)
        self.layout.addWidget(self.cfg_gral, 7)
        self.layout.addWidget(self.btn_osciloscope, 4)
        self.layout.addWidget(self.btn_fondo, 4)
        self.layout.addWidget(self.btn_measurement, 4)
        self.mainbox.setLayout(self.layout)


    def _create_data_folder(self):
        """Obtiene la carpeta de trabajo y la crea si no existe."""
        self.DATA_FOLDER = get_data_folder(self)
        self.DATA_FOLDER.mkdir(parents=True, exist_ok=True)


    def _cambiar_data_folder(self):
        """Permite al usuario cambiar la carpeta de trabajo."""
        self.DATA_FOLDER = ask_data_folder(self)
        self.DATA_FOLDER.mkdir(parents=True, exist_ok=True)


    def _createMenu(self):
        menu1 = self.menuBar()
        menu = menu1.addMenu('&Menu')
        menu.addAction('Cambiar carpeta de trabajo', self._cambiar_data_folder)
        menu.addAction('&Exit', self.close)
        conf = menu1.addMenu("&Cfg. avanzada")
        conf.addAction('&Ver/Editar', self.show_advconf_win)

        self.menu_bar = QMenuBar(menu1)
        menu1.setCornerWidget(self.menu_bar, Qt.Corner.TopRightCorner)
        self.menu_derecho  = QMenu(self.menu_bar)
        self.ayuda = self.menu_bar.addMenu("&Ayuda")
        self.ayuda.addAction('Ayuda ventana', self.show_ayuda_win)
        self.ayuda.addAction('Ace&rca', self.show_about_win)


    @pyqtSlot()
    def show_about_win(self):
        self.about_win = AboutWindow()
        self.about_win.show()


    @pyqtSlot()
    def show_ayuda_win(self):
        self.ayuda_win = VentanaAyuda(referencia="ventana-principal")
        self.ayuda_win.show()


    @pyqtSlot()
    def show_osc_win(self):
        if not self.osc_win_exist:
            self.osc_win = OscilloscopeWindow()
            self.osc_win_exist = True
            self.osc_win.show()
            self.osc_win.osc_win_closed.connect(self.close_osc_win)
        else:
            self.osc_win.close()


    @pyqtSlot()
    def show_meas_win(self):
        if not self.meas_win_exist:
            self.cfg_gral.save_settings()
            self.cfg_adv.save_settings()
            self.meas_win = MeasurementWindow(self.DATA_FOLDER)
            self.meas_win_exist = True
            self.meas_win.show()
            self.meas_win.meas_win_closed.connect(self.close_meas_win)
            self.cfg_gral.set_whole_tree("readonly")
            self.escribe_coeficientes()
        else:
            self.meas_win.close()


    def escribe_coeficientes(self):
        """
        Escribe coeficientes de conversión int16 a voltaje.

        Se utiliza solamente para procesar los archivos .RUI
        """
        dev = self.cfg_adv.get_param_value("Configuración avanzada",
                                           "Dispositivo")
        serie = self.cfg_gral.get_param_value("Parámetros generales",
                                              "Serie")
        dev_info = GetDevicesInfo().device_info(dev)
        rangos = dev_info.ai_ranges
        canal = self.cfg_adv.get_channels()[0]
        coeficientes = {}
        for rg in rangos:
            coeficientes[rg[1]] = dev_info.scaling_coeff(canal, rg)
        filename = f"S{serie:02d}-coeficientes_int_to_volt.pkl"
        with open(os.path.join(self.DATA_FOLDER, filename), 'wb') as f:
            pickle.dump(coeficientes, f)


    def show_advconf_win(self):
        if not self.advconf_win_exist:
            self.cfg_gral.save_settings()
            self.cfg_adv.save_settings()
            self.advconf_win = AdvanceConfigurationWindow(parent=self)
            self.advconf_win_exist = True
            self.advconf_win.show()
            self.advconf_win.advconf_win_closed.connect(self.close_advconf_win)
        else:
            self.advconf_win.close()


    @pyqtSlot()
    def close_osc_win(self):
        self.osc_win_exist = False


    @pyqtSlot()
    def close_meas_win(self):
        self.meas_win_exist = False
        self.cfg_gral.set_whole_tree("writable")


    @pyqtSlot()
    def close_advconf_win(self):
        self.advconf_win_exist = False
        self.cfg_adv = AdvancedParamTree(self.n_det, self.cip, reset=False)


    @pyqtSlot(object, object)
    def cfg_gral_change(self, _, changes):
        """
        Cuando se cambia cantidad de detectores y medición de CIp
        se actualizan los datos de la configuración avanzada
        """
        for param, change, data in changes:
            _childs = self.cfg_gral.params.childPath(param)
            if "Medición de CIp" in _childs and change == "value":
                self.cip = data
                self.cfg_adv.actualiza_cip()
            elif "Cadenas de medición" in _childs and change == "value":
                self.n_det = data
                self.cfg_adv.actualiza_cadenas_med(data)


    @pyqtSlot()
    def show_background_win(self):
        if not self.background_win_exist:
            self.cfg_gral.save_settings()
            self.cfg_adv.save_settings()
            self.background_win = BackgroundWindow(self.DATA_FOLDER)
            self.background_win_exist = True
            self.background_win.show()
            self.background_win.background_win_closed.connect(
                    self.close_background_win)
        else:
            self.background_win.close()


    @pyqtSlot()
    def close_background_win(self):
        self.background_win_exist = False


    def closeEvent(self, event):
        self.cfg_gral.save_settings()
        if self.osc_win_exist:
            self.osc_win.close()
        if self.meas_win_exist:
            self.meas_win.close()
        if self.background_win_exist:
            self.background_win.close()
        if self.advconf_win_exist:
            self.advconf_win.close()


if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
