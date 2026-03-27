from PyQt6 import QtGui
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *

import pyqtgraph as pg

# --- From DAQ Control --- #
from .misc_functions import calculate_mean_value


class SignalPlot(pg.PlotWidget):
    """
    """

    def __init__(self, legend=None, tipo=None):
        super().__init__()

        # Tamaño de la línea para el plot
        self.line_width = 2
        self.update_legend(legend)

        self.showGrid(True, True)

        if tipo == "time":
            self.setLabel("left", "Voltaje", units="V")
            self.setLabel("bottom", "Tiempo", units="s")
        else:
            self.setLabel("left", "Voltaje", units="V")
            self.setLabel("bottom", "Datos")


    # Temporal, hasta pensarlo mejor
    def update_legend(self, leg):
        self.legend = leg
        self.curve_colors = self.legend.colores
        self.pens = [pg.mkPen(i, width=self.line_width)
                                    for i in self.curve_colors]


    def update_plot(self, incoming_data, x_data=None):
        self.clear()
        if x_data is None:
            for i, data in enumerate(incoming_data):
                # this is kinda ugly but it works so let's roll with it
                if self.legend.legend_items[i].toggle_box.isChecked():
                    self.plot(data, clear=False, pen=self.pens[i])
        else:
            for i, data in enumerate(incoming_data):
                # this is kinda ugly but it works so let's roll with it
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

        self._name = name
        self._channel = channel
        self._color = color
        self.name = name

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
        self.text = self._name + "\n (" + str(self._channel) + ")"
        # self.curve_label.setText(self.text)
        self.toggle_box.setText(self.text)


    @property
    def color(self):
        return self._color


    @color.setter
    def color(self, col):
        self._color = col
        self.update() # llama a paintEvent


    @property
    def name(self):
        return self._name


    @name.setter
    def name(self, nam):
        # Se podría obviar mostrar el canal, por ahora lo dejo
        self._name = nam
        self.text = self._name + "\n (" + str(self._channel) + ")"
        self.toggle_box.setText(self.text)


    def set_current_mean(self, data):
        _mean = "{:.4f}".format(calculate_mean_value(data))
        self.current_mean_label.setText("Mean: " + _mean)


    def paintEvent(self, e):
        painter = QtGui.QPainter(self)
        #painter.setPen(QtGui.QPen(pg.mkColor(self._color), 6, Qt.SolidLine))
        painter.setPen(QtGui.QPen(pg.mkColor(self._color), 6,
            Qt.PenStyle.SolidLine))

        width, height = painter.device().width(), painter.device().height()
        line_length = 60
        line_start = 25
        line_height_start = 0
        painter.drawLine(line_start, line_height_start,
                         line_start + line_length, line_height_start
        )


class Legend(QWidget):
    """
    """
    def __init__(self, colores, nombres, canales):
        super().__init__()

        if len(set([len(i) for i in [colores, nombres, canales]])) !=1:
            raise ValueError("Argumentos de Legend() no tienen mismo tamaño")

        self.num_chan = len(canales)
        self.colores = colores

        self.layout = QVBoxLayout()
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.layout.setSpacing(0)
        self.legend_items = [
            LegendItem(color=color, name=nombre, channel=canal)
            for color, nombre, canal in zip(colores, nombres, canales)
        ]
        for item in self.legend_items:
            self.layout.addWidget(item)

        self.setLayout(self.layout)


    def update_num_legends(self, new_numb, chan_prop):
       """
       Agrega o quita el widget de la leyenda

       new_numb : (float) nueva cantidad de canales
       chan_prot: (list) propiedades de los canales agregados
       """
       while self.num_chan > new_numb:
           # Quito el widget del layout
           self.layout.removeWidget(self.legend_items[-1])
           self.legend_items[-1].setParent(None)
           # Quito el item de la lista
           self.legend_items.pop()
           self.num_chan -= 1
       while self.num_chan < new_numb:
           # Agrego widget a layout
           # Paso las propiedades de los canales agregados
           new_item = LegendItem(*chan_prop[self.num_chan])
           self.layout.addWidget(new_item)
           # Agrego item a la lista
           self.legend_items.append(new_item)
           self.num_chan +=1
       # Transitorio
       self.colores = [prop[0] for prop in chan_prop]


    def update_channels(self, channels):
        for i, item in enumerate(self.legend_items):
            item.channel = channels[i]


    def update_colors(self, colors):
        for i, item in enumerate(self.legend_items):
            item.color = colors[i]
        # Transitorio
        self.colores = colors


    def update_names(self, names):
        for i, item in enumerate(self.legend_items):
            item.name = names[i]


    def on_new_data(self, data):
        for i, item in enumerate(self.legend_items):
            item.set_current_mean(data[i])


if __name__ == "__main__":
    pass

