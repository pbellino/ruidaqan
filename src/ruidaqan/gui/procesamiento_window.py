#! /usr/bin/env python3

import os
import numpy as np
import importlib
import tables as tb
import pickle
from pathlib import Path
from PyQt6.QtGui import QFont, QGuiApplication
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QSize
from PyQt6.QtWidgets import (QMessageBox, QGridLayout, QLabel, QPushButton,
                             QProgressBar, QTabWidget, QWidget, QVBoxLayout,
                             QHBoxLayout, QLayout, QGroupBox, QMenu,
                             QSpinBox, QDoubleSpinBox, QComboBox, QMainWindow,
                             QFileDialog, QCheckBox, QMenuBar)
import pyqtgraph as pg

from .resultados_window import ShowSpectrumFittedValues
from .plotter import PlotProcessing
from .ventanas_ayuda import VentanaAyuda, AboutWindow
from .config import DATA_FOLDER
from ..constants import constantes_reactores as CONREAC
from ..script.data_fercin3_io import RUIFileProcessing, HDF5FileProcessing


class FitWindow(QMainWindow):
    """
    TODO
    """

    fit_win_closed = pyqtSignal()


    def __init__(self, file_name=None, from_acquisition=False):
        super().__init__()

        # Carpeta donde se leerán y gardarán datos por default
        self.data_folder = DATA_FOLDER

        self.time_filename = file_name
        self.from_acquisition = from_acquisition

        self._labels_spec = ["NAPSD1", "NAPSD2", "Re(NCPSD)"]
        self._lista_reactores = [a for a in dir(CONREAC)
                                            if not a.startswith("__") ]
        self._lista_reactores.remove("Constantes_Nucleares")

        self.init_ui()

        self.pushButton_getSpectrums.setEnabled(False)
        self.pushButton_fit.setEnabled(False)
        self.btn_grabar.setEnabled(False)
        self.pushButton_getSpectrums.setText("Estimar espectros")

        self.load_reactor_file()

        # Acción al apretar botón para leer .RUI
        self.pushButton_openfile.clicked.connect(self.get_time_file)
        # Acción para cargar constantes del reactor
        self.comboBox_reactorfile.currentTextChanged.connect(
                                                    self.load_reactor_file)
        # Acción para cargar constantes del un núcleo
        self.comboBox_coreid.activated.connect(self.load_core)
        # Acción para estimar y graficar los espectros
        self.pushButton_getSpectrums.clicked.connect(self.get_norm_spectrums)
        # Acción cuando se cambia el límite de ajuste con los spinbox
        self.spinBox_f_from.valueChanged.connect(self.region_changed_spin)
        self.spinBox_f_to.valueChanged.connect(self.region_changed_spin)
        # Acción para ajustar los espectros
        self.pushButton_fit.clicked.connect(self.fit_spectrums)
        # Acción cuando se cambia el espectro seleccionado
        self.comboBox_spec.activated.connect(self.change_spec)
        # Acción para abrir ventana con resultaos previos
        self.prev_win_exist = False
        self.btn_previos.clicked.connect(self.show_previous_win)
        # Acción para cuando se aprieta botón de cerrar
        self.btn_cerrar.clicked.connect(self.close)
        # Acción para cuando se aprieta botón de grabar
        self.btn_grabar.clicked.connect(self.graba_resultados)
        # Acción para habilitar edición de constantes de reactor
        self.checkbox_edit.stateChanged.connect(self._habilita_edicion_reactor)

        # Si se llama desde el programa de adquisición se carga directamente el
        # archivo recién medido
        if from_acquisition:
            self.pushButton_openfile.setEnabled(False)
            self.get_time_file()
            self.get_norm_spectrums()
            self.fit_spectrums()


    def init_ui(self):
        """ Define and initialize GUI """
        self.resize(QSize(1100, 600)) # ancho, alto
        self.setWindowTitle("Procesamiento y ajustes")
        self.center()
        self.showMaximized()
        self._createMenu()

        # Main layout
        gridLayout_all = QGridLayout(self)
        verticalLayout_left = QVBoxLayout()
        verticalLayout_right = QVBoxLayout()
        gridLayout_all.addLayout(verticalLayout_left, 0, 0, 1, 1)
        gridLayout_all.addLayout(verticalLayout_right, 0, 1, 1, 1)

        # Group box for header
        groupBox_header = QGroupBox("Archivo temporal")
        gridLayout_header = QGridLayout(groupBox_header)

        self.pushButton_openfile = QPushButton(groupBox_header)
        self.pushButton_openfile.setText("Cargar archivo")
        lbl_filename_title = QLabel("Nombre:")
        self.lbl_filename = QLabel(groupBox_header)

        lbl_date_title = QLabel(groupBox_header)
        lbl_date_title.setText("Fecha:")
        self.lbl_date = QLabel(groupBox_header)

        lbl_hour_title = QLabel(groupBox_header)
        lbl_hour_title.setText("Hora:")
        self.lbl_hour = QLabel(groupBox_header)

        lbl_BW_title = QLabel(groupBox_header)
        lbl_BW_title.setText("BW [Hz]:")
        self.lbl_BW = QLabel(groupBox_header)

        lbl_I1_title = QLabel(groupBox_header)
        lbl_I1_title.setText("I<sub>1</sub> [A]:")
        self.lbl_I1 = QLabel(groupBox_header)

        self.lbl_I2_title = QLabel(groupBox_header)
        self.lbl_I2_title.setText("I<sub>2</sub> [A]:")
        self.lbl_I2_title.hide()
        self.lbl_I2 = QLabel(groupBox_header)
        self.lbl_I2.hide()

        lbl_Ip_title = QLabel(groupBox_header)
        lbl_Ip_title.setText("I<sub>p</sub> [A]:")
        self.lbl_Ip = QLabel(groupBox_header)

        gridLayout_header.addWidget(self.pushButton_openfile,0,0,1,2)
        gridLayout_header.addWidget(lbl_filename_title,1,0,1,1)
        gridLayout_header.addWidget(self.lbl_filename,1,1,1,1)
        gridLayout_header.addWidget(lbl_date_title,2,0,1,1)
        gridLayout_header.addWidget(self.lbl_date,2,1,1,1)
        gridLayout_header.addWidget(lbl_hour_title,3,0,1,1)
        gridLayout_header.addWidget(self.lbl_hour,3,1,1,1)
        gridLayout_header.addWidget(lbl_BW_title,4,0,1,1)
        gridLayout_header.addWidget(self.lbl_BW,4,1,1,1)
        gridLayout_header.addWidget(lbl_I1_title,5,0,1,1)
        gridLayout_header.addWidget(self.lbl_I1,5,1,1,1)
        gridLayout_header.addWidget(self.lbl_I2_title,6,0,1,1)
        gridLayout_header.addWidget(self.lbl_I2,6,1,1,1)
        gridLayout_header.addWidget(lbl_Ip_title,7,0,1,1)
        gridLayout_header.addWidget(self.lbl_Ip,7,1,1,1)

        gridLayout_header.setRowStretch(8, 1)

        # Group box for constants
        groupBox_constants = QGroupBox("Parámetros del reactor")
        gridLayout_constants = QGridLayout(groupBox_constants)

        self.checkbox_edit = QCheckBox(groupBox_constants)
        self.checkbox_edit.setText("Habilitar edición")
        self.checkbox_edit.setCheckState(Qt.CheckState.Checked)
        lbl_reactorfile = QLabel()
        lbl_reactorfile.setText("Reactor :")
        self.comboBox_reactorfile = QComboBox(groupBox_constants)
        self.comboBox_reactorfile.addItems(self._lista_reactores)
        self.comboBox_reactorfile.setCurrentText("RA3")

        lbl_coreid = QLabel()
        lbl_coreid.setText("Núcleo :")
        self.comboBox_coreid = QComboBox(groupBox_constants)

        lbl_beta_title = QLabel()
        lbl_beta_title.setText("\u03B2<sub>eff</sub> :")
        self.lbl_beta = QLabel()

        lbl_lmbda_title = QLabel()
        lbl_lmbda_title.setText("\u039B<sup>*</sup> :")
        self.lbl_lmbda = QLabel()

        lbl_L1_title = QLabel()
        lbl_L1_title.setText("L<sub>1</sub> :")
        self.lbl_L1 = QLabel()

        lbl_Diven_title = QLabel()
        lbl_Diven_title.setText("D<sub>\u03BD</sub> :")
        self.lbl_Diven = QLabel()

        lbl_Ef_title = QLabel()
        lbl_Ef_title.setText("E<sub>fission</sub> :")
        self.lbl_Ef = QLabel()

        gridLayout_constants.addWidget(lbl_reactorfile,0,0,1,1)
        gridLayout_constants.addWidget(self.comboBox_reactorfile,0,1,1,1)
        gridLayout_constants.addWidget(lbl_coreid,1,0,1,1)
        gridLayout_constants.addWidget(self.comboBox_coreid,1,1,1,1)
        gridLayout_constants.addWidget(lbl_beta_title,2,0,1,1)
        gridLayout_constants.addWidget(self.lbl_beta,2,1,1,1)
        gridLayout_constants.addWidget(lbl_lmbda_title,3,0,1,1)
        gridLayout_constants.addWidget(self.lbl_lmbda,3,1,1,1)
        gridLayout_constants.addWidget(lbl_L1_title,4,0,1,1)
        gridLayout_constants.addWidget(self.lbl_L1,4,1,1,1)
        gridLayout_constants.addWidget(lbl_Diven_title,5,0,1,1)
        gridLayout_constants.addWidget(self.lbl_Diven,5,1,1,1)
        gridLayout_constants.addWidget(lbl_Ef_title,6,0,1,1)
        gridLayout_constants.addWidget(self.lbl_Ef,6,1,1,1)
        gridLayout_constants.addWidget(self.checkbox_edit,7,0,2,1)
        gridLayout_constants.setRowStretch(8, 1)

        # Group box for spextral estimation
        groupBox_getSpectrums = QGroupBox("Estimación espectral")
        gridLayout_getSpectrums = QGridLayout(groupBox_getSpectrums)

        lbl_Nfft_title = QLabel("Tamaño bloque:")
        self.spinBox_Nfft = QSpinBox(groupBox_getSpectrums)
        self.spinBox_Nfft.setMaximum(2**12)
        self.spinBox_Nfft.setValue(512)
        lbl_overlap_title = QLabel("Solapamiento:")
        self.spinBox_overlap = QSpinBox(groupBox_getSpectrums)
        self.spinBox_overlap.setValue(0)
        self.spinBox_overlap.setMaximum(self.spinBox_Nfft.value()-1)
        lbl_utility_freq = QLabel("Frecuencia de línea")
        self.spinBox_utility_freq = QDoubleSpinBox(groupBox_getSpectrums)
        self.spinBox_utility_freq.setSuffix(" Hz")
        self.spinBox_utility_freq.setValue(50)

        self.pushButton_getSpectrums = QPushButton(groupBox_getSpectrums)
        self.pushButton_getSpectrums.setText("Estimar espectro")

        gridLayout_getSpectrums.addWidget(lbl_Nfft_title, 0, 0, 1, 1)
        gridLayout_getSpectrums.addWidget(self.spinBox_Nfft, 0, 1, 1, 1)
        gridLayout_getSpectrums.addWidget(lbl_overlap_title, 1, 0, 1, 1)
        gridLayout_getSpectrums.addWidget(self.spinBox_overlap, 1, 1, 1, 1)
        gridLayout_getSpectrums.addWidget(lbl_utility_freq, 2, 0, 1, 1)
        gridLayout_getSpectrums.addWidget(self.spinBox_utility_freq, 2, 1, 1,1)
        gridLayout_getSpectrums.addWidget(self.pushButton_getSpectrums,3,0,1,2)
        gridLayout_getSpectrums.setRowStretch(4, 1)


        # Group box for fit controls
        groupBox_fitcontrols = QGroupBox("Controles del ajuste")
        gridLayout_fitcontrols = QGridLayout(groupBox_fitcontrols)

        lbl_selec_spec = QLabel("Espectro:")
        self.comboBox_spec = QComboBox(groupBox_fitcontrols)
        lbl_f_from_title = QLabel("Desde:")
        self.spinBox_f_from = QDoubleSpinBox(groupBox_fitcontrols)
        self.spinBox_f_from.setSuffix(" Hz")
        lbl_f_to_title = QLabel("Hasta:")
        self.spinBox_f_to = QDoubleSpinBox(groupBox_fitcontrols)
        self.spinBox_f_to.setSuffix(" Hz")
        self.pushButton_fit = QPushButton(groupBox_header)
        self.pushButton_fit.setText("Ajustar espectros")

        gridLayout_fitcontrols.addWidget(lbl_selec_spec, 0, 0, 1, 1)
        gridLayout_fitcontrols.addWidget(self.comboBox_spec, 0, 1, 1, 1)
        gridLayout_fitcontrols.addWidget(lbl_f_from_title, 1, 0, 1, 1)
        gridLayout_fitcontrols.addWidget(self.spinBox_f_from, 1, 1, 1, 1)
        gridLayout_fitcontrols.addWidget(lbl_f_to_title, 2, 0, 1, 1)
        gridLayout_fitcontrols.addWidget(self.spinBox_f_to, 2, 1, 1, 1)
        gridLayout_fitcontrols.addWidget(self.pushButton_fit, 3, 0, 1, 2)
        gridLayout_fitcontrols.setRowStretch(4, 1)

        # Left layout
        verticalLayout_left.addWidget(groupBox_header)
        verticalLayout_left.addWidget(groupBox_constants)
        verticalLayout_left.addWidget(groupBox_getSpectrums)
        verticalLayout_left.addWidget(groupBox_fitcontrols)

        # Group box for fit results
        groupBox_results = QGroupBox("Resultados del ajuste")
        gridLayout_results = QGridLayout(groupBox_results)


        # Labels para cada columna ("label", "poisición en gridlayout")
        labels_col = {
                       "A [1/Hz]":                  (0, 1),
                       "N [1/Hz]":                  (0, 2),
                       "\u03B1 [1/s]":              (0, 3),
                       "P [W]":                     (0, 4),
                       "f<sub>q</sub> [C]":         (0, 5),
                       "\u03B5/\u03B2<sup>2</sup>": (0, 6),
                      }
        # Labels para cada fila
        labels_fil = {la: (i + 1, 0) for i, la in enumerate(self._labels_spec)}
        labels = {**labels_fil, **labels_col}
        # Se general los labels para cada fila y columnas
        self.lbl_results = {}
        for labtext, pos in labels.items():
            self.lbl_results[labtext] = QLabel(groupBox_results)
            self.lbl_results[labtext].setText(labtext)
            self.lbl_results[labtext].setAlignment(Qt.AlignmentFlag.AlignCenter)
            gridLayout_results.addWidget(
                                     self.lbl_results[labtext], pos[0], pos[1])

        # Display para los números (0, 2) es alfa de NPSD2
        self.lcds = {f"{i}, {j}": (i, j)
                  for i in range(3) for j in range(6)}
        for key, pos in self.lcds.items():
            self.lcds[key] = QLabel(groupBox_results)
            self.lcds[key].setAlignment(Qt.AlignmentFlag.AlignCenter)
            gridLayout_results.addWidget(
                            self.lcds[key], pos[0] + 1, pos[1] + 1)
        # Oculto NPSD2 y NCPSD
        [self.lbl_results[l].hide() for l in self._labels_spec[1:]]
        [self.lcds[f"{i}, {j}"].hide() for i in range(1, 3) for j in range(6)]
        groupBox_results.setMinimumHeight(150)

        # Botones grabar y cerrar
        self.btn_previos = QPushButton("Datos previos")
        self.btn_grabar = QPushButton("Grabar datos")
        self.btn_cerrar = QPushButton("Cerrar")
        btns_layout = QVBoxLayout()
        btns_layout.setAlignment(Qt.AlignmentFlag.AlignBottom)
        btns_layout.addWidget(self.btn_previos)
        btns_layout.addWidget(self.btn_grabar)
        btns_layout.addWidget(self.btn_cerrar)

        right_bottom_lay = QHBoxLayout()
        right_bottom_lay.addWidget(groupBox_results, 8)
        right_bottom_lay.addLayout(btns_layout, 1)

        # Right layout
        # Gráfico de los espectros
        self.layout_graph = pg.GraphicsLayoutWidget()
        # Gráficos temporales
        self.plot_DC = PlotProcessing(("Tiempo", "Corriente"), ("s", "A"))
        self.plot_AC = PlotProcessing(("Tiempo", "Voltaje"), ("s", "V"))

        self.tabs = QTabWidget(self)
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.tabs.addTab(self.plot_DC, "DC")
        self.tabs.addTab(self.plot_AC, "AC")
        self.tabs.addTab(self.layout_graph, "Espectros")

        verticalLayout_right.addWidget(self.tabs)
        verticalLayout_right.addLayout(right_bottom_lay)

        self.mainbox = QWidget(self)
        self.mainbox.setLayout(gridLayout_all)
        self.setCentralWidget(self.mainbox)

    def _createMenu(self):
        menu1 = self.menuBar()
        # menu1.addMenu('File')

        self.menu_bar = QMenuBar(menu1)
        menu1.setCornerWidget(self.menu_bar, Qt.Corner.TopRightCorner)
        self.menu_derecho  = QMenu(self.menu_bar)
        self.ayuda = self.menu_bar.addMenu("&Ayuda")
        self.ayuda.addAction('Ayuda ventana', self.show_ayuda_win)
        self.ayuda.addAction('Ace&rca', self.show_about_win)

    @pyqtSlot()
    def show_ayuda_win(self):
        self.ayuda_win = VentanaAyuda(referencia="procesamiento-y-ajustes")
        self.ayuda_win.show()

    @pyqtSlot()
    def show_about_win(self):
        self.about_win = AboutWindow()
        self.about_win.show()

    @pyqtSlot()
    def get_time_file(self):
        """ Lee el archivo temporal .RUI o .h5 """
        if not self.from_acquisition:
            self.time_filename = QFileDialog.getOpenFileName(self,
                                     'Abrir archivo', self.data_folder,
                                     'Archivo temporal (*.RUI *.h5)')[0]
            # Se graba la carpeta seleccionada
            self.data_folder = os.path.dirname(self.time_filename)
        if len(self.time_filename) != 0:
            try:
                # Intenta abrir como HDF5
                self.time_file = HDF5FileProcessing(self.time_filename)
            except tb.HDF5ExtError:
                try:
                    # Intenta abrir como .RUI
                    self.time_file = RUIFileProcessing(self.time_filename)
                except Exception as e:
                    print("No se pudo abrir ningún archivo", e)
                else:
                    self.is_hdf5_file = False
                    self.process_time_file()
            else:
                self.is_hdf5_file = True
                self.process_time_file()


    def process_time_file(self):
       self.lbl_filename.setText(os.path.split(self.time_filename)[-1])
       date = self.time_file.date
       hour = self.time_file.hour
       if not self.is_hdf5_file:
           date = date.replace('"','')
           hour = hour.replace('"','')
       self.lbl_date.setText(date)
       self.lbl_hour.setText(hour)
       self.lbl_BW.setText(f"{self.time_file.BW:.1f}")

       # Muestra las corrientes
       _I_str = [f"{i:.2E}" for i in self.time_file.I]
       _Ip_str = f"{self.time_file.Ip:.2E}"
       self.lbl_I1.setText(_I_str[0])
       self.lbl_Ip.setText(_Ip_str)
       if self.time_file.n_det == 2:
           self.lbl_I2_title.show()
           self.lbl_I2.show()
           self.lbl_I2.setText(_I_str[1])
       else:
           self.lbl_I2_title.hide()
           self.lbl_I2.hide()

       # Fija el reactor
       try:
           reactor = self.time_file.reactor.replace('-', '')
           self.comboBox_reactorfile.setCurrentText(reactor)
           self.checkbox_edit.setCheckState(Qt.CheckState.Unchecked)
       except AttributeError:
           self.checkbox_edit.setCheckState(Qt.CheckState.Checked)

       self.pushButton_getSpectrums.setEnabled(True)
       # Grafica las señales temporales
       self.plot_temporal_signals()
       # Obtiene los espectros
       self.get_norm_spectrums()
       # Ajusta los espectros
       self.fit_spectrums()
       # Obtengo los atributos "serie", "nivel", "medicion"
       self._get_info_from_filename()


    def plot_temporal_signals(self):
        # Grafico las señales termporales
        time_vec, AC_datas, DC_datas = \
                                self.time_file.get_temporal_signals()
        if self.is_hdf5_file:
            DC_labels = self.time_file.DC_nombres
            self.plot_DC.load_plot(time_vec, DC_datas, DC_labels)
            AC_labels = self.time_file.AC_nombres
            self.plot_AC.load_plot(time_vec, AC_datas, AC_labels)
            self.tabs.setTabVisible(0, True)
        else:
            # Para un .RUI sólo están las AC
            # Invento nombres para identificarlos
            labels = ["Detector 1", "Detector 2"]
            self.plot_AC.load_plot(time_vec, AC_datas,
                                   labels[0:len(AC_datas)])
            self.tabs.setCurrentIndex(1)
            self.tabs.setTabVisible(0, False)


    @pyqtSlot()
    def load_reactor_file(self):
        self.reactor = self.comboBox_reactorfile.currentText()
        self._REAC = getattr(CONREAC, self.reactor)

        # Se fija si hay cargadas constantes de núcleos específicos
        core_list = [i for i in dir(self._REAC) if i.startswith("N")]
        if core_list:
            self.comboBox_coreid.clear()
            self.comboBox_coreid.addItems(core_list)
            self.load_core()
            self._default_constants = f"{self.reactor} - {core_list[0]}"
        else:
            # Si no hay constantes para núcleos específicos
            self.comboBox_coreid.clear()
            self.coreid = self.comboBox_coreid.currentText()

            self.REACTOR_CLS = self._REAC
            self._write_constants()
            self._default_constants = f"{self.reactor}"
        # Fija el núcleo especificado en el archivo hdf5
        try:
            nucleo = self.time_file.nucleo
            if nucleo != " ":
                nucleo = 'N' + nucleo
                self.comboBox_coreid.setCurrentText(self.time_file.nucleo)
            else:
                if nucleo not in core_list:
                    msg = (f"El núcleo {nucleo} no posee constantes asociadas. "
                           f"Se utilizan las constantes del {self.default_constants}."
                            "\nModificar el archivo 'constantes_reactores.py' "
                            "de ser necesario.")
                    button = QMessageBox.information(self,
                                              "Constantes no encontradas", msg)
        except AttributeError:
            pass


    @pyqtSlot()
    def _habilita_edicion_reactor(self):
        if self.checkbox_edit.checkState() == Qt.CheckState.Checked:
            self.comboBox_reactorfile.setEnabled(True)
            self.comboBox_coreid.setEnabled(True)
        else:
            self.comboBox_reactorfile.setEnabled(False)
            self.comboBox_coreid.setEnabled(False)


    @pyqtSlot()
    def load_core(self):
        self.coreid = self.comboBox_coreid.currentText()
        self._REAC_CORE = getattr(self._REAC, self.coreid)
        self.REACTOR_CLS = self._REAC_CORE
        self._write_constants()


    def _write_constants(self):
        self.beta_eff = self.REACTOR_CLS.BETA_EFECTIVO
        self.Lambdax = self.REACTOR_CLS.LAMBDA_REDUCIDO
        self.L1 = self.REACTOR_CLS.FACTOR_FORMA_L
        self.Diven = self.REACTOR_CLS.FACTOR_DIVEN
        self.Ef = self.REACTOR_CLS.ENERGIA_FISION

        self.lbl_beta.setText("{:.1f} pcm".format(100000*self.beta_eff))
        self.lbl_lmbda.setText("{:.2E} s".format(self.Lambdax))
        self.lbl_L1.setText("{:.4f}".format(self.L1))
        self.lbl_Diven.setText("{:.4f}".format(self.Diven))
        self.lbl_Ef.setText("{:.2E} J".format(self.Ef))


    @pyqtSlot()
    def get_norm_spectrums(self):
        uf = self.spinBox_utility_freq.value()
        self.time_file.get_normalized_spectrums(
                                         self.reactor,
                                         self.spinBox_Nfft.value(),
                                         self.spinBox_overlap.value(),
                                         freqs_to_remove = [uf, 2*uf, 3*uf],
                                         freqs_to_remove_tr = [uf, 2*uf, 3*uf]
                                         )

        # Grafica los espectros y agrega regiones de selección
        styles = {"color": "white", "font-size": "12pt"}
        self.layout_graph.clear()
        self.plots, self.regions = [], []
        for i, spec in enumerate(self.time_file.norm_spectrums):
            if i==2: spec = np.real(spec)
            p = self.layout_graph.addPlot(title=self._labels_spec[i])
            p.plot(self.time_file.f, spec, pen=pg.mkPen(color='g', width=1.5))
            p.setLabel('left', text="[1/Hz]", **styles)
            p.showGrid(x=True, y=True, alpha=0.4)
            # Región para hacer el ajuste
            r = pg.LinearRegionItem(
                                (self.time_file.f[0], self.time_file.f[-1]),
                                swapMode="block")
            r.setBounds((self.time_file.f[0], self.time_file.f[-1]))
            r.sigRegionChangeFinished.connect(self.region_changed)
            p.addItem(r)
            self.plots.append(p)
            self.regions.append(r)
            self.layout_graph.nextRow()
        self.plots[-1].setLabel('bottom', text="Frecuencia", units="Hz",
                **styles)

        # Agrega la lista al combobox para seleccionar espectro
        self.comboBox_spec.clear()
        for i, _ in enumerate(self.time_file.norm_spectrums):
            self.comboBox_spec.addItem(self._labels_spec[i])
        if i > 0: self.comboBox_spec.addItem("All")
        # Selecciono "All"
        self.comboBox_spec.setCurrentIndex(self.comboBox_spec.count() - 1)
        # Actualizo spinbox de fitRegion
        self.spinBox_f_to.setMaximum(self.time_file.f[-1])
        self.spinBox_f_from.setValue(self.time_file.f[0])
        self.spinBox_f_to.setValue(self.time_file.f[-1])
        # Valores iniciales de los spinbox de fitRegion
        if round(self.time_file.BW) == 200:
            self.spinBox_f_from.setValue(2.3)
            self.spinBox_f_to.setValue(178.9)
        elif round(self.time_file.BW) == 40:
            self.spinBox_f_from.setValue(2.8)
            self.spinBox_f_to.setValue(35.8)

        # Display para los números
        # Oculto todos salvo el primero
        [self.lbl_results[l].hide() for l in self._labels_spec[1:]]
        [self.lcds[f"{i}, {j}"].hide() for i in range(1, 3) for j in range(6)]
        # Muestro NPSD2 y NCPSD en caso de haber dos detectores
        if self.time_file.n_det == 2:
            [self.lbl_results[l].show() for l in self._labels_spec[1:]]
            [self.lcds[f"{i}, {j}"].show() for i in range(1, 3)
                                               for j in range(6)]

        self.pushButton_fit.setEnabled(True)

        self.tabs.setCurrentIndex(2)


    @pyqtSlot()
    def region_changed(self):
        _ind_curr = self.comboBox_spec.currentIndex()
        if _ind_curr != 3:
            for i, region in enumerate(self.regions):
                if self.sender() == region:
                    self.comboBox_spec.setCurrentIndex(i)
                    f1, f2 = region.getRegion()
                    self.spinBox_f_from.setValue(f1)
                    self.spinBox_f_to.setValue(f2)
                    self.spinBox_f_from.setMaximum(f2)
                    self.spinBox_f_to.setMinimum(f1)
                    break
        else:
            for region in self.regions:
                if self.sender() == region:
                    f1, f2 = region.getRegion()
                    self.spinBox_f_from.setValue(f1)
                    self.spinBox_f_to.setValue(f2)
                    self.spinBox_f_from.setMaximum(f2)
                    self.spinBox_f_to.setMinimum(f1)
            for region in self.regions:
                region.setRegion((f1, f2))


    @pyqtSlot(float)
    def region_changed_spin(self, val_ch):
        if self.sender() == self.spinBox_f_from:
            # Cambio sólo el espectro seleccionado
            _i = self.comboBox_spec.currentIndex()
            if _i < 3:
                # Cambio individualmente
                _, f2 = self.regions[_i].getRegion()
                self.regions[_i].setRegion((val_ch, f2))
            elif _i == 3:
                # Cambio todos
                for k in range(3):
                    _, f2 = self.regions[k].getRegion()
                    self.regions[k].setRegion((val_ch, f2))
                    # Pongo el que estaba, linearRegion lo cambia
                    self.comboBox_spec.setCurrentIndex(3)
        elif self.sender() == self.spinBox_f_to:
            # Cambio sólo el espectro seleccionado
            _i = self.comboBox_spec.currentIndex()
            if _i < 3:
                # Cambio individualmente
                f1, _ = self.regions[_i].getRegion()
                self.regions[_i].setRegion((f1, val_ch))
            elif _i == 3:
                # Cambio todos
                for k in range(3):
                    f1, _ = self.regions[k].getRegion()
                    self.regions[k].setRegion((f1, val_ch))
                    # Pongo el que estaba, linearRegion lo cambia
                    self.comboBox_spec.setCurrentIndex(3)


    @pyqtSlot()
    def change_spec(self):
        _cur_ind = self.comboBox_spec.currentIndex()
        if _cur_ind < 3:
            # No se selecciona "All"
            f1, f2 = self.regions[_cur_ind].getRegion()
            self.spinBox_f_from.setValue(f1)
            self.spinBox_f_to.setValue(f2)


    @pyqtSlot()
    def fit_spectrums(self):
        """ Ajusta todos los espectros a la vez """
        # Se leen las regiones para el ajuste
        intervalos = [r.getRegion() for r in self.regions]
        self.time_file.fit_spectrums(intervalos, plot=False)

        # Borro el ajuste anterior
        try:
            for p, bf in zip(self.plots, self._plots_bf):
                p.removeItem(bf)
        except AttributeError:
            # self._plots_bf aún no existe
            pass

        # Grafico el ajuste
        self._plots_bf = []
        for i, p in enumerate(self.plots):
            # Selecciono los datos del ajuste
            f1, f2 = self.regions[i].getRegion()
            ind = (self.time_file.f >= f1) & (self.time_file.f <= f2)
            if i !=2:
                data = self.time_file.norm_spectrums[i][ind]
            else:
                data = np.real(self.time_file.norm_spectrums[i][ind])
            best_fit = data + self.time_file.fit_results[i].residual
            self._plots_bf.append(
                         p.plot(self.time_file.f[ind], best_fit,
                             pen=pg.mkPen(color='r', width=3))
                                  )

        # Calcula parámetros cinéticos
        self.time_file.calcula_parametros_cineticos(self.REACTOR_CLS)
        # Pueblo los resultados
        for i, par in enumerate(self.time_file.parametros_cineticos):
            for j, lab in enumerate(par.values()):
                # Distintos formatod dependiendo del prámetro
                _str = f"{lab:.2E}" if lab is not None else ""
                if j in [2, 3, 5]:
                    # Para alfa, potencia y efe_over_beta2
                    if lab is not None: _str = f"{lab:.1f}"
                self.lcds[f"{i}, {j}"].setText(_str)

        self.btn_grabar.setEnabled(True)
        self.tabs.setCurrentIndex(2)


    @pyqtSlot()
    def show_previous_win(self):
        if not self.prev_win_exist:
            # La ventana no existe
            _serie = self.serie if hasattr(self, 'serie') else None
            self.prev_win = ShowSpectrumFittedValues(_serie, self.data_folder)
            self.prev_win.show()
            self.prev_win_exist = True
            self.prev_win.prev_win_closed.connect(self.close_previous_win)
            if _serie is not None:
                # Hay un archivo .RUI cargado
                if self.prev_win.serie is None:
                    # No se encontró la serie
                    del self.prev_win
                    self.prev_win_exist = False
                else:
                    # Se abre el archivo y no se deja cambiarlo
                    self.prev_win.cargar_btn.setEnabled(False)
            else:
                # No hay un archivo .RUI cargado
                # Se deja cambiar el archivo
                self.prev_win.cargar_btn.setEnabled(True)

        else:
            # La ventana ya existe
            self.prev_win.close()


    @pyqtSlot()
    def graba_resultados(self):
        _data = self._format_fitresults()
        if not self.prev_win_exist:
            # Antes de mandar los datos me fijo si existe el archivo
            file_pkl = f"S{self.serie:03d}-resultados_ajustes.pkl"
            file_pkl_path = os.path.join(self.data_folder, file_pkl)
            if os.path.exists(file_pkl_path):
                # Abro la ventana
                self.prev_win = ShowSpectrumFittedValues(self.serie,
                                                         self.data_folder)
                # Agrego los datos
                self.prev_win.add_new_data(_data)
            else:
                # Lo escribo con los primeros datos
                with open(file_pkl_path, 'wb') as f:
                    pickle.dump(_data, f)
                # Abro la ventana
                self.prev_win = ShowSpectrumFittedValues(self.serie,
                                                         self.data_folder)
            self.prev_win_exist = True
            self.prev_win.show()
            self.prev_win.prev_win_closed.connect(self.close_previous_win)
        else:
            # Agrego los datos
            self.prev_win.add_new_data(_data)


    def _get_info_from_filename(self):
        _file = os.path.split(self.time_filename)[-1]
        self.serie = int(_file.split('-')[0][1:])
        self.nivel = int(_file.split('-')[1][1:])
        self.medicion = int(_file.split('-')[-1].split('.')[0])


    def _format_fitresults(self):
        """
        Fromatea los resultados del ajuste para grabarlos
        """
        # La serie, nivel y medición se leen del nombre del archivo para un
        _lbls = ["NPSD1", "NPSD2", "NCPSD"]
        _data = []
        for i, di in enumerate(self.time_file.parametros_cineticos):
            _data.append(
                         [self.nivel,
                          self.medicion,
                          round(self.time_file.BW),
                          _lbls[i],
                          self.time_file.Ip,                          # Ip
                          self.time_file.I[i] if i!=2 else None,      # Ii
                          di['alfa'],
                          di['potencia'],
                          di['fq'],
                          di['efi_over_beta2']
                         ]
                        )
        return np.asarray(_data)


    @pyqtSlot()
    def close_previous_win(self):
        self.prev_win_exist = False


    def center(self):
        """ Center window on screen """
        qr = self.frameGeometry()
        cp = QGuiApplication.primaryScreen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())


    def closeEvent(self, event):
        self.fit_win_closed.emit()
        event.accept()


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    win = FitWindow()
    win.show()
    sys.exit(app.exec_())

