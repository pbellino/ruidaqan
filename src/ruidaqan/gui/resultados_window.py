#! /usr/bin/env python3

import os
import numpy as np
import pickle
import pyqtgraph as pg
from uncertainties import unumpy, ufloat, umath
import darkdetect

from PyQt6 import QtCore, QtGui
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (QVBoxLayout, QPushButton, QWidget, QTableView,
                             QFormLayout, QLabel, QHBoxLayout, QMenu, QMenuBar,
                             QAbstractItemView, QMessageBox,
                             QTabWidget, QGroupBox, QGridLayout, QFileDialog,
                             QMainWindow)

from .ventanas_ayuda import VentanaAyuda, AboutWindow
from .ScientificDoubleSpinBox import ScientificDoubleSpinBox
from .appconfig import get_data_folder
from ..script.data_fercin3_io import (FitResults, normaliza_resultados,
                                      COLUMNAS_RESULTADOS)
from ..script.fit_models import ajuste_lineal, weighted_average

# Columna con la incerteza de la potencia usada en cada fila ('ajuste' o
# 'lotes')
COL_INCERTEZA = COLUMNAS_RESULTADOS.index("Incerteza P")


class FittingTableModel(QtCore.QAbstractTableModel):
    """
    TODO
    """


    def __init__(self, data=None, labels=None):
        super().__init__()

        self._data = data
        self.labels = labels


    def data(self, index, role):
        # Para formatear visualización del contenido de las celdas
        if role == Qt.ItemDataRole.DisplayRole:
            _nul = ufloat(0, 0)
            value = self._data[index.row(), index.column()]
            if isinstance(value, type(_nul)):
                if umath.isnan(value):
                    return ""
                else:
                    return f"{value:.2e}"
            elif isinstance(value, float):
                return f"{value:.2f}"
            elif isinstance(value, type(umath.sin(_nul))):
                # Los parámetros correlacionados tienen otro tipo de datos
                # distinto al ufloat
                _v = ufloat(value.n, value.s)
                return f"{_v:.2e}"
        # Para alinear contenido de las celdas
        if role == Qt.ItemDataRole.TextAlignmentRole:
            value = self._data[index.row(), index.column()]
            return int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignCenter)


    def rowCount(self, index):
        return self._data.shape[0]


    def columnCount(self, index):
         return self._data.shape[1]


    def headerData(self, section, orientation, role):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return str(self.labels[section])
            elif orientation == Qt.Orientation.Vertical:
                return str(section + 1)


class FittingView(QWidget):
    def __init__(self, data=None, labels=None, fit='linear'):
        super().__init__()

        self.labels = labels
        self.mag = [la.split()[0] for la in labels]
        self.text = {"I1": 'I<sub>1</sub>',
                     "I2": 'I<sub>2</sub>',
                     "Ip": 'I<sub>p</sub>',
                     "p": 'p',
                     "fq1": 'f<sub>q1</sub>',
                     "fq2": 'f<sub>q2</sub>',
                     "alfa": '\u03B1',
                     "e1/b2": "\u03B5<sub>1</sub>/\u03B2<sup>2</sup>",
                     "e2/b2": "\u03B5<sub>2</sub>/\u03B2<sup>2</sup>",
                     }
        self.units = {"I1": 'A', "I2": "A", "Ip": "A", "p": "W", "fq1": "C",
                      "alfa": "1/s", "fq2": "C", "e1/b2": "", "e2/b2": ""}
        self.fit = fit

        self.data_orig = np.copy(data)

        self.model = FittingTableModel(data, self.labels)
        self.view = QTableView()
        self.view.setModel(self.model)

        self.init_ui()

        self.del_btn.clicked.connect(self.delete)
        self.orig_btn.clicked.connect(self.load_original)

        self._update_plot_fit()


    def init_ui(self):
        self.resize(1000, 600)

        # Left
        groupBox_btns = QGroupBox("Selección de datos")
        self.orig_btn = QPushButton(groupBox_btns)
        self.orig_btn.setText("Todos")
        self.del_btn = QPushButton(groupBox_btns)
        self.del_btn.setText("Borrar")
        btns_layout = QHBoxLayout(groupBox_btns)
        btns_layout.addWidget(self.orig_btn)
        btns_layout.addWidget(self.del_btn)

        self.view.setMaximumWidth(480)

        self.left_layout = QVBoxLayout()
        self.left_layout.addWidget(self.view)
        self.left_layout.addWidget(groupBox_btns)

        # Right
        self.graph = pg.GraphicsLayoutWidget()
        self.plot = self.graph.addPlot()
        #self.plot.setLogMode(True, True)
        self.groupBox_results = QGroupBox("Resultados del ajuste")
        results_layout = QGridLayout(self.groupBox_results)

        # Labels columnas
        labels_col = {
                       "a ":              (0, 1),
                       "b ":              (0, 2),
                       "r<sup>2</sup> ":  (0, 3),
                           }
        # Labels filas
        if self.fit == "constant":
            labels_fil = {la: (i + 1, 0) for i, la in enumerate(self.labels[1:])}
        else:
            #labels_fil = {la: (i + 1, 0) for i, la in enumerate(self.labels[1:])}
            labels_fil = {"": (1, 0)}
        labels = {**labels_fil, **labels_col}
        self.lbl_results = {}
        for labtext, pos in labels.items():
            self.lbl_results[labtext] = QLabel(self.groupBox_results)
            self.lbl_results[labtext].setText(labtext)
            self.lbl_results[labtext].setAlignment(Qt.AlignmentFlag.AlignCenter)
            results_layout.addWidget(self.lbl_results[labtext], pos[0], pos[1])

        # Display para los resultados de los ajustes grid 2x3
        self.lcds = {f"{i}, {j}": (i, j)
                  for i in range(3) for j in range(4)}
        for key, pos in self.lcds.items():
            self.lcds[key] = QLabel(self.groupBox_results)
            self.lcds[key].setAlignment(Qt.AlignmentFlag.AlignCenter)
            results_layout.addWidget(
                            self.lcds[key], pos[0], pos[1])


        self.right_layout = QVBoxLayout()
        self.right_layout.addWidget(self.graph)
        self.right_layout.addWidget(self.groupBox_results)

        self.main_layout = QHBoxLayout()
        self.main_layout.addLayout(self.left_layout)
        self.main_layout.addLayout(self.right_layout)

        self.setLayout(self.main_layout)


    def update_data(self, data):
        self.data_orig = np.copy(data)
        self.model._data = data
        self.model.layoutChanged.emit()
        self._update_plot_fit()
        self.view.setColumnWidth(0, 150)
        self.view.setColumnWidth(1, 150)
        self.view.setColumnWidth(2, 150)


    def _update_plot_fit(self):
        self.plot.clear()
        # Es para saber cuántos parámetros tiene el widget basado en los datos
        # que se le pasan. Es un parche que parece funcionar
        self.num_param = self.model._data.shape[1] - 1

        s1 = pg.ScatterPlotItem(size=10)
        _x = unumpy.nominal_values(self.model._data[:, 0])
        if _x.size > 0:
            if isinstance(_x[0], type(ufloat(0, 0))):
                _x = unumpy.nominal_values(_x)
            beam = max(_x) * 0.01
        else:
            beam = 0
        _y1 = unumpy.nominal_values(self.model._data[:, 1])
        _y1er = unumpy.std_devs(self.model._data[:, 1])
        s1.addPoints(x=_x, y=_y1, pen={'color': 'r', 'width':2})
        _x = np.asarray(_x, dtype=float)
        err1 = pg.ErrorBarItem(x=_x , y=_y1, height=2*_y1er, pen='r',
                beam=beam)
        self.plot.addItem(s1)
        self.plot.addItem(err1)
        _y_label = self.labels[1]
        if self.num_param == 2:
            s2 = pg.ScatterPlotItem(size=10)
            _y2 = unumpy.nominal_values(self.model._data[:, 2])
            _y2er = unumpy.std_devs(self.model._data[:, 2])
            s2.addPoints(x=_x, y=_y2, pen={'color': 'b', 'width':2})
            err2 = pg.ErrorBarItem(x=_x , y=_y2, height=2*_y2er, pen='b',
                    beam=beam)
            self.plot.addItem(s2)
            self.plot.addItem(err2)
            #self.plot.setLogMode(x=True, y=False)
        # Bug https://github.com/pyqtgraph/pyqtgraph/issues/1604
        # No andan bien las escalas logarítmicas
        # self.plot.setLogMode(x=True, y=True)
        # Formato de los ejes
        if self.fit == "constant":
            units_x = "W"
            units_y = self.units[self.mag[1]]
        else:
            units_x = "A"
            units_y = "W" if "p" in self.mag else "A"
        styles = {"color": "white", "font-size": "12pt"}
        self.plot.setLabel(axis='left', text=self.text[self.mag[1]],
                           units=self.units[self.mag[1]], **styles)
        self.plot.setLabel(axis='right', units=self.units[self.mag[1]],
                           color='k')
        self.plot.setLabel(axis='bottom', text=self.text[self.mag[0]],
                           units=self.units[self.mag[0]], **styles)
        self.plot.setLabel(axis='top', units=self.units[self.mag[0]],
                           color='k')
        self.plot.showGrid(True, True)

        dat_fit = self.model._data
        # Ajusta, grafica y muestra valores del ajuste
        if dat_fit.size > 0:
            if self.num_param == 1:
                # Quito toda la fila
                dat_fit = dat_fit[~(unumpy.isnan(dat_fit).any(axis=1))]
                x = unumpy.nominal_values(dat_fit[:, 0])
                y_n = unumpy.nominal_values(dat_fit[:, 1])
                y_s = unumpy.std_devs(dat_fit[:, 1])
                if self.fit == "constant":
                    mean_y, std_y = weighted_average(y_n,  1 / y_s**2)
                    self.lbl_results["a "].setVisible(False)
                    self.lbl_results["b "].setVisible(False)
                    self.lbl_results["r<sup>2</sup> "].setVisible(False)
                    self.lcds["1, 1"].setText(f"{ufloat(mean_y, std_y)}")
                    self.groupBox_results.setTitle(
                            "Resultados del ajuste y = a ")
                    self.plot.plot(x, np.ones_like(x)*mean_y, pen={'color':'r',
                              'width':1, "style": QtCore.Qt.PenStyle.DashLine})
                else:
                    self.a, b, r_sq, _, y_fit = ajuste_lineal(x, y_n, y_s)
                    self.lcds["1, 1"].setText(f"{self.a}")
                    self.lcds["1, 2"].setText(f"{b}")
                    self.lcds["1, 3"].setText(f"{r_sq:.6f}")
                    self.groupBox_results.setTitle(
                            "Resultados del ajuste y = a x + b ")
                    self.plot.plot(x, y_fit, pen={'color': 'r', 'width':1,
                        "style": QtCore.Qt.PenStyle.DashLine})
            elif self.num_param == 2:
                _tmp = dat_fit[:,[0, 1]]
                dat_fit_1 = _tmp[~(unumpy.isnan(_tmp).any(axis=1))]
                x1 = unumpy.nominal_values(dat_fit_1[:, 0])
                y1_n = unumpy.nominal_values(dat_fit_1[:, 1])
                y1_s = unumpy.std_devs(dat_fit_1[:, 1])
                _tmp = dat_fit[:,[0, 2]]
                dat_fit_2 = _tmp[~(unumpy.isnan(_tmp).any(axis=1))]
                y2_n = unumpy.nominal_values(dat_fit_2[:, 1])
                y2_s = unumpy.std_devs(dat_fit_2[:, 1])
                # Por simplicidad asumo que si tengo dos parámetros sólo me
                # interesa el promedio de ellos (uno para cada detector)
                mean_1, std_1 = weighted_average(y1_n,  1 / y1_s**2)
                mean_2, std_2 = weighted_average(y2_n,  1 / y2_s**2)
                # Oculto los que no uso
                self.lbl_results["a "].setVisible(False)
                self.lbl_results["b "].setVisible(False)
                self.lbl_results["r<sup>2</sup> "].setVisible(False)
                # Escribo los resultados
                self.lcds["1, 1"].setText(f"{ufloat(mean_1, std_1)}")
                self.lcds["2, 1"].setText(f"{ufloat(mean_2, std_2)}")
                self.groupBox_results.setTitle("Resultados del ajuste y = a ")
                # Grafico los resultados
                self.plot.plot(x1, np.ones_like(x1)*mean_1, pen={'color':'r',
                              'width':1, "style": QtCore.Qt.PenStyle.DashLine})
                self.plot.plot(x1, np.ones_like(x1)*mean_2, pen={'color':'b',
                              'width':1, "style": QtCore.Qt.PenStyle.DashLine})


    def show_fitted_data(self, values, best_fit):
        """
        Muestra ajuste en el gráfico y valores numéricos
        """
        pass


    def delete(self):
        """
        TODO: no dejar borrar primer columna
        """
        indexes = self.view.selectedIndexes()
        if indexes:
            for index in indexes:
                self.model._data[index.row(), index.column()] = ufloat(np.nan,
                        np.nan)

            self.model.layoutChanged.emit()
            self.view.clearSelection()
            self._update_plot_fit()


    def load_original(self):
        self.model._data[:, :] = self.data_orig
        self.model.layoutChanged.emit()
        self._update_plot_fit()


class TableModel(QtCore.QAbstractTableModel):
    """
    Modelo para acumular y procesar resultados de los ajustes
    """
    def __init__(self, data=None, header=None):
        super(TableModel, self).__init__()

        self._data = data or []
        self.header = header


    def data(self, index, role):
        # Colores a utlizar dependiendo del tema
        if darkdetect.isDark:
            fondo_par = "DimGrey"
            fondo_impar = "DarkSlateGrey"
            fondo_vacio = "SlateGrey"
        else:
            fondo_par = "#3182bd"
            fondo_impar = "#9ecae1"
            fondo_vacio = "#3182bd"

        # Para formatear visualización del contenido de las celdas
        if role == Qt.ItemDataRole.DisplayRole:
            value = self._data[index.row()][index.column()]
            if value is None: return ""
            # Formato para mostrar floats
            if index.column() in [4, 5, 8]:
                return f"{value:.3E}"
            elif index.column() == 10:
                # Valor p del test por lotes
                return f"{value:.2g}" if np.isfinite(value) else ""
            else:
                return f"{value}"
            if index.column() in [6, 7, 8]:
                return f"{value:.2f}"
        # Para alinear contenido de las celdas
        if role == Qt.ItemDataRole.TextAlignmentRole:
            value = self._data[index.row()][index.column()]
            return int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignCenter)
        if role == Qt.ItemDataRole.BackgroundRole:
            value = self._data[index.row()][index.column()]
            # Se resaltan las mediciones en las que se usó la incerteza por
            # lotes (el test rechazó la incerteza del ajuste)
            if (index.column() == COL_INCERTEZA and isinstance(value, str)
                    and value.startswith("lotes")):
                return QtGui.QColor("#e6550d")
            if self._data[index.row()][0] % 2 == 0:
                if value is None:
                    return QtGui.QColor(fondo_vacio)
                else:
                    return QtGui.QColor(fondo_par)
            else:
                if value is None:
                    return QtGui.QColor(fondo_vacio)
                else:
                    return QtGui.QColor(fondo_impar)


    def rowCount(self, index):
        return len(self._data)


    def columnCount(self, index):
        try:
            return len(self._data[0])
        except IndexError:
            return 0


    def headerData(self, section, orientation, role):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return str(self.header[section])
            elif orientation == Qt.Orientation.Vertical:
                return str(section + 1)


class ShowSpectrumFittedValues(QMainWindow):
    """
    Clase para acumular y procesar los resultados del ajuste

    TODO: Se deben deshabilitar (no se pueden ocultar) los tabs innecesarios
    que sobran cuando se mide con un detector
    """

    prev_win_closed = pyqtSignal()

    def __init__(self, serie=None, folder=None):
        """
        Serie: int
            Identificación de la serie
        """
        super().__init__()
        self.serie = serie

        # Carpeta donde se leerán y gardarán datos poe default
        self.data_folder = folder if folder is not None else str(get_data_folder())

        self.init_ui()
        self.tabs_view.setEnabled(False)
        self.tabs_view.setEnabled(False)
        if self.serie is not None: self.cargar_btn.setEnabled(False)

        self.header = ["Nivel", "Medición", "BW [Hz]", "Espectro", "Ip [A]",
                       "Ii [A]", "alfa [1/s]", "p [W]", "fq [C]", "e/b2",
                       "p lotes (P)", "Incerteza (P)"]

        # Connect the button.
        self.del_btn.clicked.connect(self.delete)
        self.end_btn.clicked.connect(self.end_measurement)
        self.cargar_btn.clicked.connect(self.cargar_archivo)

        # Cuando se cambian los puntos del ajuste (borrando o usando todos los
        # datos) se actualiza el resultado mostrado en la parte de "resumen"
        _widgets = [self.p_Ip_fit,
                    self.p_I1_fit,
                    self.p_I2_fit,
                    self.alfa_fit,
                    self.efi_fit,
                    self.fq1_fit,
                    self.fq2_fit,
                   ]
        for _w in _widgets:
            _w.orig_btn.clicked.connect(self._copy_resumen)
            _w.del_btn.clicked.connect(self._copy_resumen)

        # Cálculo de las predicciones automático
        self.dsp_pot.valueChanged.connect(self.prediccion_pot_I)
        self.dsp_I1.valueChanged.connect(self.prediccion_pot_I)
        self.dsp_I2.valueChanged.connect(self.prediccion_pot_I)
        self.dsp_Ip.valueChanged.connect(self.prediccion_pot_I)


        if serie is not None:
            try:
                self.cargar_archivo()
            except IOError:
                # Si no se puede abrir el archivo, se abre vacia
                pass


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
        self.ayuda_win = VentanaAyuda(referencia="resultados")
        self.ayuda_win.show()


    @pyqtSlot()
    def show_about_win(self):
        self.about_win = AboutWindow()
        self.about_win.show()


    @pyqtSlot(float)
    def prediccion_pot_I(self, new_value):
        """
        Predice potencia o corrientes en base a coeficientes de calibración
        """
        old_p = self.dsp_pot.value()
        old_I1 = self.dsp_I1.value()
        try:
            old_I2 = self.dsp_I2.value()
        except: pass
        old_Ip = self.dsp_Ip.value()

        fp = self.p_Ip_fit.a if hasattr(self.p_Ip_fit, 'a') else None
        f1 = self.p_I1_fit.a if hasattr(self.p_I1_fit, 'a') else None
        f2 = self.p_I2_fit.a if hasattr(self.p_I2_fit, 'a') else None
        if self.sender() == self.dsp_pot:
            # Si cambio la potencia
            if fp:
                # Cambio Ip
                new_Ip = new_value / fp
                self.dsp_Ip.setValue(new_Ip.n)
            if f1:
                # Cambio I1
                new_I1 = new_value / f1
                self.dsp_I1.setValue(new_I1.n)
            if f2:
                # CAmbio I2
                new_I2 = new_value / f2
                self.dsp_I2.setValue(new_I2.n)
        elif self.sender() == self.dsp_Ip:
            # Si cambio Ip
            if fp:
                # Cambio potencia
                new_p = new_value * fp
                self.dsp_pot.setValue(new_p.n)
            if fp and f1:
                # Cambio I1
                new_I1 = new_value * fp / f1
                self.dsp_I1.setValue(new_I1.n)
            if fp and f2:
                # Cambio I2
                new_I2 = new_value * fp / f2
                self.dsp_I2.setValue(new_I2.n)
        elif self.sender() == self.dsp_I1:
            # Si cambio I1
            if f1:
                # Cambio potencia
                new_p = new_value * f1
                self.dsp_pot.setValue(new_p.n)
            if f1 and fp:
                # Cambio Ip
                new_Ip = new_value * f1 / fp
                self.dsp_Ip.setValue(new_Ip.n)
            if f1 and f2:
                # Cambio I2
                new_I2 = new_value * f1 / f2
                self.dsp_I2.setValue(new_I2.n)
        elif self.sender() == self.dsp_I2:
            # Si cambio I2
            if f2:
                # Cambio potencia
                new_p = new_value * f2
                self.dsp_pot.setValue(new_p.n)
            if f2 and fp:
                # Cambio Ip
                new_Ip = new_value * f2 / fp
                self.dsp_Ip.setValue(new_Ip.n)
            if f2 and f1:
                # Cambio I1
                new_I1 = new_value * f2 / f1
                self.dsp_I1.setValue(new_I1.n)


    @pyqtSlot()
    def cargar_archivo(self):
        if self.serie is not None:
            # Nombre del archivo con los datos
            self.file_name = f"S{self.serie:03d}-resultados_ajustes.pkl"
            self.file_path = os.path.join(self.data_folder, self.file_name)
        else:
            # Abre diálogo para cargar el archivo
            self.load_file()

        self.model = TableModel(header=self.header)

        self.load()
        # Variable para saber si la tabla está vacia o no
        self.empty_table = False if np.asarray(self.model._data).size > 0 else True
        self.tableView.setModel(self.model)

        self.set_column_width()


    def _update_fit_widgets(self):
        """
        Actualiza los widgets con valores y gráficos del ajuste
        """
        self.fit_res = FitResults(self.file_path)

        if self.fit_res.n_det == 1:
            # oculto tabs
            self.tabs_corrientes.setTabVisible(1, False)
            self.tabs_corrientes.setTabVisible(4, False)
            self.tabs_parametros.setTabVisible(2, False)
            # Saco I2 de las predicciones
            try:
                self.estimaciones_layout.removeRow(self.dsp_I2)
                # Cuando no existe, da error
            except: pass
        else:
            # Muestro al segundo detector
            self.lbl_resumen["NAPSD2"].show()
            [self.lcds[f"1, {j}"].show() for j in range(3)]

        # Si hay sólo un nivel, no hago ajustes lineales
        if len(set(self.model._data[:, 0])) > 1:
            # Se actualiza todo
            self.fit_res.fit_p_vs_I(plot=False)
            self.fit_res.fit_Ip_vs_I(plot=False)

            # Potencias usadas para los ajustes (de NCPSD)
            _p_uarr = unumpy.uarray(self.fit_res._pot_mag,
                                    self.fit_res._pot_std)
            _dat_p_I1 = np.vstack([self.fit_res.Is[0].to_numpy(), _p_uarr]).T
            self.p_I1_fit.update_data(_dat_p_I1)
            if self.fit_res.n_det == 2:
                _dat_p_I2 = np.vstack(
                                    [self.fit_res.Is[1].to_numpy(), _p_uarr]).T
                self.p_I2_fit.update_data(_dat_p_I2)
                _dat_Ip_I2 = np.vstack(
                                    [self.fit_res.Is[1].to_numpy(),
                                     self.fit_res.Is[2].to_numpy()]
                                    ).T
                self.Ip_I2_fit.update_data(_dat_Ip_I2)

            _dat_p_Ip = np.vstack([self.fit_res.Is[2].to_numpy(), _p_uarr]).T
            self.p_Ip_fit.update_data(_dat_p_Ip)
            _dat_Ip_I1 = np.vstack(
                                    [self.fit_res.Is[0].to_numpy(),
                                     self.fit_res.Is[2].to_numpy()]
                                    ).T
            self.Ip_I1_fit.update_data(_dat_Ip_I1)
        #else:
        #    data = np.empty((0,0))
        #    self.Ip_I1_fit.data_orig = np.copy(data)
        #    self.Ip_I1_fit.model._data = data
        #    self.Ip_I1_fit.model.layoutChanged.emit()
        #    #self.Ip_I1_fit._update_plot_fit()

        # De acá en más se actualiza siempre
        self.fit_res.average_parameters(plot=False)


        # Alfas
        _alfas = self.fit_res.alfa_bylevel.apply(np.asarray)
        _pot = self.fit_res.pote_bylevel.apply(np.asarray)
        _p, _a = 2 * [np.asarray([])]
        for p, a in zip(_pot, _alfas):
            _p = np.hstack([_p, p * np.ones_like(a)])
            _a = np.hstack([_a, a])
        self.alfa_fit.update_data(np.vstack([_p, _a]).T)

        # fqs y efis
        _fq1 = self.fit_res.fq_1_bylevel.apply(np.asarray)
        _fq2 = self.fit_res.fq_2_bylevel.apply(np.asarray)
        _ef1 = self.fit_res.efi_1_bylevel.apply(np.asarray)
        _ef2 = self.fit_res.efi_2_bylevel.apply(np.asarray)
        _p, _f1, _f2, _e1, _e2 = 5 * [np.asarray([])]
        if self.fit_res.n_det == 2:
            for p, f1, f2, e1, e2 in zip(_pot, _fq1, _fq2, _ef1, _ef2):
                _p = np.hstack([_p, p * np.ones_like(f1)])
                _f1 = np.hstack([_f1, f1])
                _f2 = np.hstack([_f2, f2])
                _e1 = np.hstack([_e1, e1])
                _e2 = np.hstack([_e2, e2])
            self.fq1_fit.update_data(np.vstack(
                                     [self.fit_res.I_fq1.to_numpy(), _f1]).T)
            self.fq2_fit.update_data(np.vstack(
                                     [self.fit_res.I_fq2.to_numpy(), _f2]).T)
            self.efi_fit.update_data(np.vstack([_p, _e1, _e2]).T)
        else:
            for p, f1, e1 in zip(_pot, _fq1, _ef1):
                _p = np.hstack([_p, p * np.ones_like(f1)])
                _f1 = np.hstack([_f1, f1])
                _e1 = np.hstack([_e1, e1])
            self.fq1_fit.update_data(np.vstack(
                                     [self.fit_res.I_fq1, _f1]).T)
            self.efi_fit.update_data(np.vstack([_p, _e1]).T)

        self._copy_resumen()


    def _copy_resumen(self):
        """
        Copia los valores de cada ajuste al cuadro de resumen
        """
        # fp
        self.lbl_fp.setText(self.p_Ip_fit.lcds["1, 1"].text())
        # f1
        self.lcds["0, 0"].setText(self.p_I1_fit.lcds["1, 1"].text())
        # f2
        self.lcds["1, 0"].setText(self.p_I2_fit.lcds["1, 1"].text())
        # Alfa
        self.lbl_alfa.setText(self.alfa_fit.lcds["1, 1"].text())
        # efi1
        self.lcds["0, 1"].setText(self.efi_fit.lcds["1, 1"].text())
        # efi2
        self.lcds["1, 1"].setText(self.efi_fit.lcds["2, 1"].text())
        # fq1
        self.lcds["0, 2"].setText(self.fq1_fit.lcds["1, 1"].text())
        # fq2
        self.lcds["1, 2"].setText(self.fq2_fit.lcds["1, 1"].text())


    def init_ui(self):
        self.resize(1000, 890)
        # Para centrar la ventana
        self.center()
        self.showMaximized()
        self._createMenu()


        self.setWindowTitle("Resultados de las mediciones")

        # Botón para borrar datos de la tabla
        self.del_btn = QPushButton("Borrar")
        self.btns_lay = QHBoxLayout()
        self.btns_lay.addStretch()
        self.btns_lay.addWidget(self.del_btn)
        # Botón para finalizar
        self.end_btn = QPushButton("Cerrar")
        self.cargar_btn = QPushButton("Abrir archivo")

        self.tableView = QTableView()
        # Selecciono por filas
        self.tableView.setSelectionBehavior(
                QAbstractItemView.SelectionBehavior.SelectRows)

        self.tabs_view = QTabWidget()

        tabs_1_widget = QWidget()
        tabs_1_lay = QVBoxLayout()
        tabs_1_lay.addWidget(self.tableView)
        tabs_1_lay.addLayout(self.btns_lay)
        tabs_1_widget.setLayout(tabs_1_lay)
        self.tabs_view.addTab(tabs_1_widget, "Datos")

        # Variables vacias para inicializar
        ones_1 = np.empty((0,2), dtype=float)
        ones_2 = np.empty((0,3), dtype=float)

        # Sub Tabs de ajuste lineales de corrientes
        tabs_ajustes = QTabWidget()
        self.p_I1_fit = FittingView(ones_1, labels=["I1 [A]", "p [W]"])
        self.p_I2_fit = FittingView(ones_1, labels=["I2 [A]", "p [W]"])
        self.p_Ip_fit = FittingView(ones_1, labels=["Ip [A]", "p [W]"])
        self.Ip_I1_fit = FittingView(ones_1, labels=["I1 [A]", "Ip [A]"])
        self.Ip_I2_fit = FittingView(ones_1, labels=["I2 [A]", "Ip [A]"])

        self.tabs_corrientes = QTabWidget()
        self.tabs_corrientes.addTab(self.p_I1_fit, "p vs I1")
        self.tabs_corrientes.addTab(self.p_I2_fit, "p vs I2")
        self.tabs_corrientes.addTab(self.p_Ip_fit, "p vs Ip")
        self.tabs_corrientes.addTab(self.Ip_I1_fit, "Ip vs I1")
        self.tabs_corrientes.addTab(self.Ip_I2_fit, "Ip vs I2")
        tabs_2_widget = QWidget()
        tabs_2_lay = QVBoxLayout()
        tabs_2_lay.addWidget(self.tabs_corrientes)
        tabs_2_widget.setLayout(tabs_2_lay)

        # Sub Tabs de ajuste parámetros
        self.tabs_parametros = QTabWidget()
        self.alfa_fit = FittingView(ones_1, labels=["p [W]", "alfa [1/s]"],
                                    fit="constant")
        self.fq1_fit = FittingView(ones_1, labels=["I1 [A]", "fq1 [C]"],
                                   fit="constant")
        self.fq2_fit = FittingView(ones_1, labels=["I2 [A]", "fq2 [C]"],
                                   fit="constant")
        self.efi_fit = FittingView(ones_2, labels=["p [W]", "e1/b2", "e2/b2"],
                                   fit="constant")
        self.tabs_parametros.addTab(self.alfa_fit, "Alfa")
        self.tabs_parametros.addTab(self.fq1_fit, "fq1")
        self.tabs_parametros.addTab(self.fq2_fit, "fq2")
        self.tabs_parametros.addTab(self.efi_fit, "Eficiencia")
        tabs_3_widget = QWidget()
        tabs_3_lay = QVBoxLayout()
        tabs_3_lay.addWidget(self.tabs_parametros)
        tabs_3_widget.setLayout(tabs_3_lay)

        self.tabs_view.addTab(tabs_2_widget, "Ajustes")
        self.tabs_view.addTab(tabs_3_widget, "Parámetros")

        # Resumen de parámetros
        groupBox_comunes = QGroupBox("Parámetros comunes")
        lbl_fp_title = QLabel(groupBox_comunes)
        lbl_fp_title.setText("f<sub>p</sub> [W/A] :")
        self.lbl_fp = QLabel(groupBox_comunes)
        lbl_alfa_title = QLabel(groupBox_comunes)
        lbl_alfa_title.setText("\u03B1 [1/s] :")
        self.lbl_alfa = QLabel(groupBox_comunes)
        comunes_layout = QGridLayout(groupBox_comunes)
        comunes_layout.addWidget(lbl_fp_title, 0, 0, 1, 1)
        comunes_layout.addWidget(self.lbl_fp, 0, 1, 1, 1)
        comunes_layout.addWidget(lbl_alfa_title, 1, 0, 1, 1)
        comunes_layout.addWidget(self.lbl_alfa, 1, 1, 1, 1)

        groupBox_detectores = QGroupBox("Parámetros individuales")
        detectores_layout = QGridLayout(groupBox_detectores)
        # Nombres de filas y columnas
        labels_spec = ["NAPSD1", "NAPSD2"]
        labels_fil = {la: (i + 1, 0) for i, la in enumerate(labels_spec)}
        labels_col = {
                      "f<sub>i</sub> [W/A]":         (0, 1),
                      "\u03B5/\u03B2<sup>2</sup>":   (0, 2),
                      "f<sub>q</sub> [C]":           (0, 3),
                     }
        labels = {**labels_fil, **labels_col}
        self.lbl_resumen = {}
        for lab, pos in labels.items():
            self.lbl_resumen[lab] = QLabel(groupBox_detectores)
            self.lbl_resumen[lab].setText(lab)
            self.lbl_resumen[lab].setAlignment(Qt.AlignmentFlag.AlignCenter)
            detectores_layout.addWidget(self.lbl_resumen[lab], pos[0], pos[1])
        # Para los valores
        self.lcds = {f"{i}, {j}": (i, j)
                    for i in range(2) for j in range(3)}
        for key, pos in self.lcds.items():
            self.lcds[key] = QLabel(groupBox_detectores)
            self.lcds[key].setAlignment(Qt.AlignmentFlag.AlignCenter)
            detectores_layout.addWidget(self.lcds[key], pos[0] + 1, pos[1] + 1)
        # Inicialmente sólo se muestra el detector 1
        self.lbl_resumen["NAPSD2"].hide()
        [self.lcds[f"1, {j}"].hide() for j in range(3)]


        # Para estimar potencia y corrientes
        groupBox_estimaciones = QGroupBox("Predicciones")
        self.estimaciones_layout = QFormLayout(groupBox_estimaciones)
        self.dsp_pot = ScientificDoubleSpinBox(groupBox_estimaciones)
        self.dsp_pot.setSuffix(" W")
        self.dsp_I1 = ScientificDoubleSpinBox(groupBox_estimaciones)
        self.dsp_I1.setSuffix(" A")
        self.dsp_I2 = ScientificDoubleSpinBox(groupBox_estimaciones)
        self.dsp_I2.setSuffix(" A")
        self.dsp_Ip = ScientificDoubleSpinBox(groupBox_estimaciones)
        self.dsp_Ip.setSuffix(" A")
        self.estimaciones_layout.addRow("Potencia:", self.dsp_pot)
        self.estimaciones_layout.addRow("I1:", self.dsp_I1)
        self.estimaciones_layout.addRow("I2:", self.dsp_I2)
        self.estimaciones_layout.addRow("Ip:", self.dsp_Ip)

        self.resumen_layout = QHBoxLayout()
        self.resumen_layout.addWidget(groupBox_comunes, 1)
        self.resumen_layout.addWidget(groupBox_detectores, 3)
        self.resumen_layout.addWidget(groupBox_estimaciones, 1)

        # Botones inferiores
        bottom_layout = QHBoxLayout()
        self.lbl_openfile_title = QLabel("Archivo leido:")
        self.lbl_openfile = QLabel()
        bottom_layout.addWidget(self.cargar_btn)
        bottom_layout.addWidget(self.lbl_openfile_title)
        bottom_layout.addWidget(self.lbl_openfile)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.end_btn)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.tabs_view, 10)
        self.layout.addLayout(self.resumen_layout, 2)
        self.layout.addLayout(bottom_layout, 1)

        self.mainbox = QWidget(self)
        self.mainbox.setLayout(self.layout)
        self.setCentralWidget(self.mainbox)


    def center(self):
        """ Center window on screen """
        qr = self.frameGeometry()
        cp = QtGui.QGuiApplication.primaryScreen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())


    @pyqtSlot()
    def load_file(self):
        self.file_path = QFileDialog.getOpenFileName(self,
                    "Abrir archivo", self.data_folder, "pkl files (*.pkl)")[0]
        # Guardo el nombre del archivo
        self.file_name = os.path.split(self.file_path)[-1]
        # Guardo la carpeta abierta
        self.data_folder = os.path.dirname(self.file_path)
        if len(self.file_name) == 0:
            dlg = QMessageBox(self)
            dlg.setWindowTitle("Error")
            dlg.setIcon(QMessageBox.Icon.Critical)
            dlg.setText(f"No se especificó archivo para leer")
            button = dlg.exec()
            raise ValueError("No se especificó archivo para leer")


    def set_column_width(self):
        # Ancho de las columnas
        for i in [0, 1, 2, 3]:
            self.tableView.setColumnWidth(i, 80)
        for i in [4, 5, 6, 7, 8, 9]:
            self.tableView.setColumnWidth(i, 160)
        self.tableView.setColumnWidth(10, 100)
        self.tableView.setColumnWidth(COL_INCERTEZA, 130)


    def add_new_data(self, data):
        """
        Método para agregar datos a la tabla
        """
        if self._measurement_exists(data):
            # No se guardan los datos
            dlg = QMessageBox(self)
            dlg.setWindowTitle("Error")
            dlg.setIcon(QMessageBox.Icon.Critical)
            _msg = (f"En el archivo {self.file_path} ya existen datos para",
                    "el nivel y medición actual. Para reeemplazarlos, primero",
                    "se deben borrar los viejos")
            dlg.setText(" ".join(_msg))
            button = dlg.exec()
        else:
            # Se guardan los datos (ambos en el formato actual de columnas)
            self.model._data = np.concatenate(
                (normaliza_resultados(self.model._data),
                 normaliza_resultados(data)), axis=0)
            self.model.layoutChanged.emit()
            self.save()
            self._update_fit_widgets()
            if self.empty_table: self.set_column_width()


    def _measurement_exists(self, data):
        """
        Comprueba si el nivel y medición ya existen en los datos guardados
        """
        _new_level = data[:, 0][0]
        _new_meas = data[:, 1][0]
        _niv_med = tuple(map(tuple, self.model._data[:, [0, 1]]))
        if (_new_level, _new_meas) in _niv_med:
            return True
        else:
            return False


    def delete(self):
        """
        Borra datos seleccionado
        """
        indexes = self.tableView.selectedIndexes()
        if indexes:
            # Selecciono un elemento por cada fila
            ind_to_remove = [indexes[i] for i in range(0, len(indexes),
                                                len(self.model._data[0]))]

            for ind in sorted(ind_to_remove, reverse=True):
                #del self.model._data[ind.row()]
                self.model._data = np.delete(self.model._data, (ind.row()),
                                             axis=0)
            self.model.layoutChanged.emit()
            self.tableView.clearSelection()
            # No conviene que se grabe la tabla si se borran datos
            self.save()
            self._update_fit_widgets()
        # Si se borraron todos los datos
        if self.model.columnCount(0)==0: self.empty_table=True


    def end_measurement(self):
        self.prev_win_closed.emit()
        self.close()


    def closeEvent(self, event):
        self.prev_win_closed.emit()
        event.accept()
        if self.serie is not None:
            self.save()


    def save(self):
        with open(self.file_path, 'wb') as f:
            pickle.dump(self.model._data, f)


    def load(self):
        try:
            with open(self.file_path, "rb") as f:
                # Los archivos anteriores al test por lotes tienen 10
                # columnas: se completan con las nuevas vacías. Al grabar,
                # el archivo queda en el formato nuevo.
                self.model._data = normaliza_resultados(pickle.load(f))
            self.model.layoutChanged.emit()
            self._update_fit_widgets()
            self.lbl_openfile.setText(self.file_path)
            self.tabs_view.setEnabled(True)
            self.tabs_view.setEnabled(True)
        except IOError:
            dlg = QMessageBox(self)
            dlg.setWindowTitle("Error")
            dlg.setIcon(QMessageBox.Icon.Critical)
            dlg.setText(f"No se pudo abrir el archivo {self.file_path}")
            button = dlg.exec()
            self.cargar_btn.setEnabled(True)
            self.serie = None
            raise


if __name__ == "__main__":
    from PyQt5 import QtWidgets
    import sys

    app = QtWidgets.QApplication(sys.argv)
    window = ShowSpectrumFittedValues()
    #window = ShowSpectrumFittedValues(98)
    window.show()
    app.exec()

