#! /usr/bin/env python3

"""GUI for the neutron noise measurement program"""

import sys
import os
from PyQt6.QtCore import Qt, pyqtSlot, pyqtSignal
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QLabel, QPushButton, QDialog, QDialogButtonBox,
                             QCheckBox, QMenu, QMenuBar)
from .parameters import GeneralParamTree, AdvancedParamTree, EspMedParamTree
from .acquisition_window import AcquisitionWindow, RangeAdjustmentWindow
from .ventanas_ayuda import VentanaAyuda
from .oscilloscope_window import OscilloscopeWindow
from .procesamiento_window import FitWindow
import ruidaqan
if ruidaqan.DEBUG_MODE:
    from .reader_debug import GetDevicesInfo
else:
    from .reader import GetDevicesInfo


class DialogFileExists(QDialog):
    """
    Diálogo para tratar con archivos existentes

    Tal vez habría que moverlo a otro archivo
    """
    def __init__(self, filename):
        super().__init__()
        self.filename = filename

        self.setWindowTitle("Archivo existente")

        QBtn = QDialogButtonBox.StandardButton.Ok | \
                                QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.layout = QVBoxLayout()
        message = QLabel(
                f"El archivo {filename} ya existe ¿se lo sobre escribe?")
        self.layout.addWidget(message)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)


class AdvanceConfigurationWindow(QMainWindow):
    """
    Ventana de configuración avanzada

    """

    advconf_win_closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        # Se leen cantidad de detectores y medición de CIp de la configuración
        # general
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.cfg_gral = GeneralParamTree(reset=False)
        self.n_det = self.cfg_gral.get_param_value(
                             "Parámetros generales", "Cadenas de medición")
        self.cip = self.cfg_gral.get_param_value(
                             "Parámetros generales", "Medición de CIp")

        self.cfg_adv = AdvancedParamTree(self.n_det, self.cip, reset=False)
        self.cfg_adv.set_whole_tree("readonly")
        self.devices = GetDevicesInfo()
        self.dev_names = self.devices.dev_names

        self.setGeometry(360, 30, 350, 690)
        self.setWindowTitle("Configuración avanzada")
        self.checkbox = QCheckBox("Editar configuración", self)
        layout = QVBoxLayout()
        layout.addWidget(self.checkbox)
        layout.addWidget(self.cfg_adv)

        self.mainbox = QWidget(self)
        self.mainbox.setLayout(layout)
        self.setCentralWidget(self.mainbox)

        self._createMenu()

        self.cfg_adv.paramChange.connect(self.cfg_adv_change)
        self.checkbox.stateChanged.connect(self._toggle_edit)



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
        self.ayuda_win = VentanaAyuda(referencia="configuracion-avanzada")
        self.ayuda_win.show()


    @pyqtSlot(int)
    def _toggle_edit(self, state):
        """ Permite editar la configuraciń avanzada """
        if state == 2:
            self.cfg_adv.set_whole_tree("writable")
        elif state == 0:
            self.cfg_adv.set_whole_tree("readonly")


    @pyqtSlot(object, object)
    def cfg_adv_change(self, _, changes):
        for param, change, data in changes:
            _childs = self.cfg_adv.params.childPath(param)
            # Se actualizan los canales si se cambia el dispositivo
            if "Dispositivo" in _childs and change == "value":
                # Cambio canal y coeficientes en todos los canales
                self.cfg_adv.update_device(data)


    def closeEvent(self, event):
        """ Manage closing oscilloscope window """
        self.cfg_adv.save_settings()
        self.advconf_win_closed.emit()
        event.accept()


class MeasurementWindow(QMainWindow):
    """
    Measurement window GUI

    Configure parameters for a specific measurement
    """
    meas_win_closed = pyqtSignal()

    def __init__(self, data_folder):
        super().__init__()

        self.DATA_FOLDER = data_folder

        self.cfg_gral = GeneralParamTree(reset=False)
        self.n_det = self.cfg_gral.get_param_value("Parámetros generales",
                                            "Cadenas de medición")
        self.cip = self.cfg_gral.get_param_value("Parámetros generales",
                                            "Medición de CIp")
        self.cfg_esp = EspMedParamTree(self.n_det, self.cip, reset=True)

        self.setGeometry(360, 30, 350, 690)
        self.setWindowTitle("Configuración medición")

        layout = QVBoxLayout()
        self.label = QLabel("Configuraciones de cada medición")
        self.btn_osciloscope = QPushButton("Osciloscopio")
        self.btn_rangos = QPushButton("Comenzar medición")

        layout.addWidget(self.label)
        layout.addWidget(self.cfg_esp)
        layout.addWidget(self.btn_osciloscope)
        layout.addWidget(self.btn_rangos)

        self.mainbox = QWidget(self)
        self.mainbox.setLayout(layout)
        self.setCentralWidget(self.mainbox)

        self._createMenu()

        # Osciloscopio
        self.osc_win_exist = False
        self.btn_osciloscope.clicked.connect(self.show_osc_win)
        # Ventana ajuste de rangos
        self.rangeadj_win_exist = False
        self.btn_rangos.clicked.connect(self.show_rangeadj_win)
        # Ventana medición ruido
        self.acq_win_exist = False
        # Ventana ajuste
        self.fit_win_exist = False
        # Ventana ajuste
        self.fit_win_exist = False

        self.cfg_esp.set_whole_tree('writable')


    def _createMenu(self):
        menu1 = self.menuBar()
        ver_menu = menu1.addMenu('&Ver')
        ver_menu.addAction('Ventana &ajustes', self.show_fit_win)

        self.menu_bar = QMenuBar(menu1)
        menu1.setCornerWidget(self.menu_bar, Qt.Corner.TopRightCorner)
        self.menu_derecho  = QMenu(self.menu_bar)
        self.ayuda = self.menu_bar.addMenu("&Ayuda")
        self.ayuda.addAction('Ayuda ventana', self.show_ayuda_win)


    @pyqtSlot()
    def show_ayuda_win(self):
        self.ayuda_win = VentanaAyuda(
                            referencia="configuracion-de-cada-medicion")
        self.ayuda_win.show()


    def output_file_exists(self):
        """
        Define el nombre del archvivo en que se guardarán los datos

        output_file_HDF: Nombre para el formato nuevo
        """

        serie = self.cfg_gral.get_param_value("Parámetros generales", "Serie")
        nivel = self.cfg_esp.get_param_value("Parámetros medición",
                                             "Medición", "Nivel")
        medicion = self.cfg_esp.get_param_value("Parámetros medición",
                                                "Medición", "Medición")
        self.output_file_HDF = f"S{serie:03d}-N{nivel}-{medicion}.h5"

        self.file_path = os.path.join(self.DATA_FOLDER, self.output_file_HDF)

        if os.path.isfile(self.file_path):
            dlg = DialogFileExists(self.file_path)
            if dlg.exec():
                # Se sobreescribe
                return False
            else:
                # Se cancela
                return True


    @pyqtSlot()
    def show_fit_win(self):
        if not self.fit_win_exist:
            self.fit_win = FitWindow()
            self.fit_win_exist = True
            self.fit_win.show()
            self.fit_win.fit_win_closed.connect(self.close_fit_win)


    @pyqtSlot()
    def close_fit_win(self):
        self.fit_win_exist = False


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
    def close_osc_win(self):
        self.osc_win_exist = False


    @pyqtSlot()
    def show_rangeadj_win(self):
        if not self.rangeadj_win_exist:
            # Se fija si existe el archivo de salida
            if not self.output_file_exists():
                self.btn_rangos.setEnabled(False)
                self.cfg_esp.save_settings()
                self.rangeadj_win = RangeAdjustmentWindow("Rangos")
                self.rangeadj_win_exist = True
                self.rangeadj_win.show()
                self.rangeadj_win.rangeadj_win_closed.connect(
                                                     self.close_rangeadj_win)
                self.rangeadj_win.rangeadj_adjusted.connect(
                                                        self.range_adjusted)
                self.cfg_esp.set_whole_tree('readonly')
        else:
            self.rangeadj_win.close()
            self.cfg_esp.set_whole_tree('writable')


    @pyqtSlot()
    def range_adjusted(self):
        # Una vez que se ajustan los rangos, se comienza la medición
        self.show_acq_win()


    @pyqtSlot()
    def close_rangeadj_win(self):
        self.rangeadj_win_exist = False
        self.btn_rangos.setEnabled(True)
        if not self.acq_win_exist:
            self.cfg_esp.set_whole_tree('writable')


    @pyqtSlot()
    def show_acq_win(self):
        if not self.acq_win_exist:
            self.cfg_esp.save_settings()
            self.acq_win = AcquisitionWindow(self.file_path)
            self.acq_win_exist = True
            self.acq_win.show()
            self.acq_win.acq_win_closed.connect(self.close_acq_win)
            self.cfg_esp.set_whole_tree('readonly')
        else:
            self.acq_win.close()
            self.cfg_esp.set_whole_tree('writable')


    @pyqtSlot()
    def close_acq_win(self):
        self.btn_rangos.setEnabled(True)
        self.acq_win_exist = False
        self.cfg_esp.set_whole_tree('writable')


    def closeEvent(self, event):
        self.meas_win_closed.emit()
        if self.acq_win_exist:
            self.acq_win.close()
        if self.rangeadj_win_exist:
            self.rangeadj_win.close()


if __name__ == '__main__':
    pass
