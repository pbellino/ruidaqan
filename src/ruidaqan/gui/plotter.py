from PyQt6 import QtGui
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *

import pyqtgraph as pg
import numpy as np

# --- From DAQ Control --- #
from .misc_functions import calculate_mean_value, calculate_spectrum_gui


class PlotProcessing(QWidget):
    """
    Widget para graficar durante el procesamiento
    """
    def __init__(self, axis_lbls=("", ""), units=("", "")):
        super().__init__()

        self.curve_colors = ["g", "r", "c", "b", "y", "m", "w"]

        self.model = QtGui.QStandardItemModel()

        self.view = QListView()
        self.view.setModel(self.model)
        self.plotWidget = pg.PlotWidget()
        self.legend = self.plotWidget.addLegend()
        self.plotWidget.showGrid(True, True, alpha=0.4)
        styles = {"color": 'white', "font-size": "12pt"}
        self.plotWidget.setLabel("bottom", axis_lbls[0], units=units[0],
                                  **styles)
        self.plotWidget.setLabel("top", "", units=units[0], color='k')
        self.plotWidget.setLabel("left", axis_lbls[1], units=units[1],
                                 **styles)
        self.plotWidget.setLabel("right", units=units[1], color='k')
        self.plotWidget.showGrid(x=True, y=True, alpha=0.4)

        self.layout = QHBoxLayout()
        self.layout.addWidget(self.plotWidget, 8)
        self.layout.addWidget(self.view, 1)
        self.setLayout(self.layout)

        self.model.itemChanged.connect(self.update_plot)


    def load_plot(self, x_data, datas, labels):
        """
        Carga por primera vez los datos par agraficar

        labels es una lista con el nombre de cada elemento de datas

        datas y labels deben ser listas de igual tamaño

        x_data es un solo vector compartido por todos los datas
        """
        self.x_axis = x_data
        self.datas = datas
        self.labels = labels
        # Limpia la lista de labels
        self.model.clear()
        # Limpia el gráfico
        self.plotWidget.clear()
        for i, data in enumerate(datas):
            # Agrego items a la lista de labels
            item = QtGui.QStandardItem(labels[i])
            item.setFlags(
                   Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            item.setData(
               QVariant(Qt.CheckState.Checked), Qt.ItemDataRole.CheckStateRole)
            self.model.appendRow(item)
            # Agrego gŕafico
            self.plot(x_data, data, labels[i], self.curve_colors[i])
        self._change_legend_size()


    @pyqtSlot()
    def update_plot(self):
        """ Actualiza los gráficos dependiendo qué está chequeado """
        if hasattr(self, "x_axis"):
            self.plotWidget.clear()
            for i, data in enumerate(self.datas):
                if self.model.item(i).checkState() == Qt.CheckState.Checked:
                    self.plot(self.x_axis, data, self.labels[i],
                              self.curve_colors[i])
            self._change_legend_size()


    def _change_legend_size(self):
        for item in self.legend.items:
            for single_item in item:
                 if isinstance(single_item, pg.graphicsItems.LabelItem.LabelItem):
                    single_item.setText(single_item.text, size="12pt")


    def plot(self, x, y, plotname, color):
        pen = pg.mkPen(color=color)
        self.plotWidget.plot(x, y, name=plotname, pen=pen)


class TabsPlot(QWidget):
    """
    Widget para graficar los datos durante la adquisición
    """

    def __init__(self, cfg_adv, cfg_meas):
        super().__init__()

        self.n_det = cfg_adv.n_det
        self.cip = cfg_adv.cip
        self.channels = cfg_adv.get_channels()
        self.labels = cfg_adv.get_channels_labels()
        self.fs = 2 * cfg_meas.get_param_value("Parámetros medición", "DAQ",
                                               "BW manual")
        # Indices de las dc's
        self.dc_indx = [3 * i + 1 for i in range(self.n_det)]
        if self.cip: self.dc_indx.append(self.n_det*3)
        # Indices de las ac's
        self.ac_indx = [3 * i for i in range(self.n_det)]

        self.init_ui()

        # Para mostrar espectro promediadiado parcial durante la medición
        self.PSD_promedio = 0.0
        # Registro de la cantidad de historias promediadas
        self.n = 0


    def init_ui(self):

        self.lgnd_DC = Legend(
                [self.channels[i] for i in self.dc_indx],
                [self.labels[i] for i in self.dc_indx]
                             )
        self.lgnd_AC = Legend(
                [self.channels[i] for i in self.ac_indx],
                [self.labels[i] for i in self.ac_indx]
                             )
        self.lgnd_PSD = Legend(
                [self.channels[i]for i in self.ac_indx],
                [self.labels[i].replace("AC", "PSD") for i in self.ac_indx]
                              )

        self.plot_DC = SignalPlot(self.lgnd_DC, tipo="time")
        self.plot_AC = SignalPlot(self.lgnd_AC, tipo="time")
        self.plot_PSD = SignalPlot(self.lgnd_PSD, tipo="spectrum")

        layout_DC = QHBoxLayout()
        layout_AC = QHBoxLayout()
        layout_PSD = QHBoxLayout()

        layout_DC.addWidget(self.plot_DC)
        layout_DC.addWidget(self.lgnd_DC)
        widget_DC = QWidget()
        widget_DC.setLayout(layout_DC)

        layout_AC.addWidget(self.plot_AC)
        layout_AC.addWidget(self.lgnd_AC)
        widget_AC = QWidget()
        widget_AC.setLayout(layout_AC)

        layout_PSD.addWidget(self.plot_PSD)
        layout_PSD.addWidget(self.lgnd_PSD)
        widget_PSD = QWidget()
        widget_PSD.setLayout(layout_PSD)

        tabs = QTabWidget(self)
        tabs.setTabPosition(QTabWidget.TabPosition.North)
        tabs.addTab(widget_AC, "AC")
        tabs.addTab(widget_PSD, "Espectros")
        tabs.addTab(widget_DC, "DC")

        layout = QVBoxLayout()
        layout.addWidget(tabs)
        self.setLayout(layout)


    def update_plots(self, incoming_data):
        data_AC = incoming_data[self.ac_indx, :]
        f_PSD, data_PSD = calculate_spectrum_gui(data_AC, self.fs)
        # Espectro promedio
        self.PSD_promedio = \
                        (data_PSD + self.n * self.PSD_promedio ) / (self.n + 1)
        self.n += 1
        data_DC = incoming_data[self.dc_indx, :]

        # Para graficar
        # Construyo el vector temporal
        time = np.arange(data_AC.shape[1]) / self.fs
        self.plot_AC.update_plot(data_AC, time)
        self.plot_PSD.update_plot(self.PSD_promedio, f_PSD)
        self.plot_DC.update_plot(data_DC, time)

        # Para poner promedio en leyendas
        self.lgnd_AC.on_new_data(data_AC)
        self.lgnd_PSD.on_new_data(data_PSD)
        self.lgnd_DC.on_new_data(data_DC)


# Graph Widget
class SignalPlot(pg.PlotWidget):
    """
    """

    def __init__(self, legend=None, tipo=None):
        super().__init__()
        # PlotWidget super functions
        self.line_width = 1
        self.legend = legend

        if self.legend is None:  # default colors if no legend has been created
            self.curve_colors = ["g", "r", "c", "b", "y", "m", "w"]
        else:
            self.curve_colors = self.legend.curve_colors

        self.pens = [pg.mkPen(i, width=self.line_width) for i in self.curve_colors]
        self.showGrid(x=True, y=True)

        styles = {"color": "white", "font-size": "12pt"}
        if tipo == "spectrum":
            self.setLabel("left", "PSD", **styles, units="V<sup>2</sup>/Hz")
            self.setLabel("bottom", "Frecuencia", units="Hz", **styles)
        elif tipo == "time":
            self.setLabel("left", "Voltaje", units="V", **styles)
            self.setLabel("bottom", "Tiempo", units="s", **styles)
        else:
            self.setLabel("left", "Voltaje", units="V", **styles)
            self.setLabel("bottom", "Datos", **styles)
        self.setLabel("right", units=" ", color='k')
        self.setLabel("top", units=" ", color='k')


    def update_plot(self, incoming_data, x_data=None):
        self.clear()
        if x_data is None:
            # Si no se pasan valores para eje x
            for i, data in enumerate(incoming_data):
                # this is kinda ugly but it works so let's roll with it
                if self.legend.legend_items[i].toggle_box.isChecked():
                    self.plot(data, clear=False, pen=self.pens[i])
        else:
            # Si se pasan valores para eje x
            for i, data in enumerate(incoming_data):
                if self.legend.legend_items[i].toggle_box.isChecked():
                    self.plot(x_data, data, clear=False, pen=self.pens[i])


class LegendItem(QWidget):
    def __init__(self, color, name, channel):
        super().__init__()
        self.curve_label = QLabel()
        self.curve_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.current_mean_label = QLabel()
        self.current_mean_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.toggle_box = QCheckBox("Test")
        self.toggle_box.setChecked(True)

        self.color = color
        self.name = name
        self.channel = channel

        layout = QVBoxLayout()
        # layout.addWidget(self.curve_label)
        layout.addWidget(self.toggle_box)
        layout.addWidget(self.current_mean_label)
        layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(layout)
        self.update()  # calls paintEvent

    @property
    def channel(self):
        return self._channel

    @channel.setter
    def channel(self, ch):
        self._channel = ch
        self.text = self.name + "\n (" + str(self._channel) + ")"
        self.curve_label.setText(self.text)
        self.toggle_box.setText(self.text)

    def set_current_mean(self, data):
        _mean = "{:.4f}".format(calculate_mean_value(data))
        self.current_mean_label.setText("Mean: " + _mean)

    def paintEvent(self, e):
        painter = QtGui.QPainter(self)
        painter.setPen(QtGui.QPen(pg.mkColor(self.color), 4, Qt.PenStyle.SolidLine))

        width, height = painter.device().width(), painter.device().height()
        line_length = 40
        line_start = 25
        line_height_start = 0
        painter.drawLine(line_start, line_height_start,
                         line_start + line_length, line_height_start
                         )


class Legend(QWidget):
    def __init__(self, channels, names):
        super().__init__()

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.curve_colors = ["g", "r", "c", "b", "y", "m", "w"]

        self.legend_items = [ LegendItem(color=self.curve_colors[i],
                                         name=names[i], channel=channels[i]
                                         ) for i, name in enumerate(channels)
                            ]
        for item in self.legend_items:
            layout.addWidget(item)

        self.setLayout(layout)


    def on_new_data(self, data):
        for i, item in enumerate(self.legend_items):
            item.set_current_mean(data[i])
