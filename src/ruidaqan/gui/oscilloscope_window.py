import sys
import numpy as np
from PyQt6 import QtGui
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (QMenu, QMenuBar, QMainWindow, QGridLayout,
                             QPushButton, QWidget)
# --- From DAQ Control --- #
from .parameters import OscilloscopeParamTree
from .plotter_oscilloscope import SignalPlot, Legend
from .ventanas_ayuda import VentanaAyuda
import ruidaqan
if ruidaqan.DEBUG_MODE:
    from .reader_debug import SignalReader, GetDevicesInfo
else:
    from .reader import SignalReader, GetDevicesInfo


class OscilloscopeWindow(QMainWindow):

    osc_win_closed = pyqtSignal()

    def __init__(self):
        super().__init__()

        # Se cargan configuraciones avanzadas
        self.cfg_osc = OscilloscopeParamTree(n_chan=2, reset=True)

        self.init_ui()
        self.thread_exist = False

        # Connect the output signal from changes in the param tree to change
        self.start_signal_btn.clicked.connect(self.start_signal_btn_click)
        # Acción para botón de cerrar
        self.cerrar_btn.clicked.connect(self.close)
        # Señal cuando se modifica el número de canales
        self.cfg_osc.params.param(
                "Configuración", "Cantidad de canales"
                ).sigValueChanged.connect(self.cambio_num_canales)
        # Señal cuando se modifica el dispositivo
        self.cfg_osc.params.param(
                "Configuración", "Dispositivo"
                ).sigValueChanged.connect(self.actualiza_dispositivo)
        # Señal cuando se modifica cualquier cosa
        self.cfg_osc.params.param(
                "Configuración"
                ).sigTreeStateChanged.connect(self.cambio_configuracion)

    def init_ui(self):
        """ Define and initialize GUI """
        self.setGeometry(10, 30, 1300, 690)
        self.setWindowTitle("Osciloscopio")

        layout = QGridLayout()

        self.legend = Legend(
                             self.cfg_osc.get_colors(),
                             self.cfg_osc.get_names(),
                             self.cfg_osc.get_channels(),
                      )

        # TODO: update legend frequency on startup with param tree values
        #   use signals instead of passing in legend might be better
        self.plotter = SignalPlot(self.legend, tipo="time")

        self.start_signal_btn = QPushButton("Comenzar adquisición")
        self.cerrar_btn = QPushButton("Cerrar")

        layout.addWidget(self.cfg_osc, 0, 0, 80, 30)
        layout.addWidget(self.plotter, 0, 30, 90, 60)
        layout.addWidget(self.start_signal_btn, 78, 0, 10, 30)
        layout.addWidget(self.cerrar_btn, 83, 0, 10, 30)
        layout.addWidget(self.legend, 0, 99, 90, 10)

        self.mainbox = QWidget(self)
        self.mainbox.setLayout(layout)
        self.setCentralWidget(self.mainbox)

        self._createMenu()

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
        self.ayuda_win = VentanaAyuda(referencia="osciloscopio")
        self.ayuda_win.show()

    def init_daq_io(self):
        # initiate read threads for analog input
        self.fs = self.cfg_osc.get_param_value( "Configuración", "Frecuencia")

        self.read_thread = SignalReader(
            sample_rate=self.cfg_osc.get_param_value(
                "Configuración", "Frecuencia"
            ),
            sample_size=self.cfg_osc.get_param_value(
                "Configuración", "Datos lectura"
            ),
            channels=self.cfg_osc.get_channels(),
            ranges=self.cfg_osc.get_ranges(),
            reading_type="float",
            terminal_cfg="RSE",
        )
        # Señal para graficar los datos
        # -Grafica en función de los datos
        # self.read_thread.incoming_data.connect(self.plotter.update_plot)
        # -Grafica en función del tiempo
        self.read_thread.incoming_data.connect(self._add_x_axis_and_plot)
        # Señal para procesar los datos
        self.read_thread.incoming_data.connect(self.legend.on_new_data)


    @pyqtSlot(object)
    def _add_x_axis_and_plot(self, in_data):
        time = np.arange(in_data.shape[1]) / self.fs
        self.plotter.update_plot(in_data, time)


    @pyqtSlot()
    def start_signal_btn_click(self):
        # TODO: Esto está bastante feo, pensar en serio.
        # Está hecho así para aprovechar las clases de adquisicón
        if self.thread_exist:
        #if 'read_thread' in dir(self) and self.thread_exist:
            print("Finaliza la adquisición")
            self.read_thread.is_running = False
            self.read_thread.wait()
            self.cfg_osc.save_settings()
            self.start_signal_btn.setText("Comenzar adquisición")
            self.thread_exist = False
            # Configuración editable (Transitorio)
            self.cfg_osc.set_whole_tree('writable')
        else:
            self.init_daq_io()
            print("Comienza la adquisición")
            self.read_thread.start()
            self.start_signal_btn.setText("Detener adquisición")
            self.thread_exist = True
            # Configuración no editable (Transitorio)
            self.cfg_osc.set_whole_tree('readonly')


    @pyqtSlot(object, object)
    def cambio_num_canales(self, _, change):
        self.cfg_osc.actualizar_numero_canales(change)
        # Obtengo las propiedades de los canales agregados
        # Paso todos, Legend() se encarga de filtrarlos
        prop = list(zip(
                        self.cfg_osc.get_colors(),
                        self.cfg_osc.get_names(),
                        self.cfg_osc.get_channels()
                       )
                    )
        self.legend.update_num_legends(change, prop)
        self.legend.update_channels(self.cfg_osc.get_channels())

        # Transitorio, hasta pensarlo bien
        self.plotter.update_legend(self.legend)


    @pyqtSlot(object, object)
    def cambio_configuracion(self, _, changes):
        for param, change, data in changes:
            _childs = self.cfg_osc.params.childPath(param)
            if _childs is not None:
                if "Color" in _childs:
                    self.legend.update_colors(self.cfg_osc.get_colors())
                    self.plotter.update_legend(self.legend)
                elif "Nombre" in _childs:
                    self.legend.update_channels(self.cfg_osc.get_channels())
                    self.plotter.update_legend(self.legend)
                elif "Identificación" in _childs:
                    self.legend.update_names(self.cfg_osc.get_names())
                    self.plotter.update_legend(self.legend)
                #TODO: lo de plotter es transitorio


    @pyqtSlot(object, object)
    def actualiza_dispositivo(self, new_dev):
        self.cfg_osc.device = new_dev.value()
        self.legend.update_channels(self.cfg_osc.get_channels())


    def closeEvent(self, event):
        if self.thread_exist:
            self.read_thread.is_running = False
            self.read_thread.wait()
            self.thread_exist = False
        self.osc_win_closed.emit()
        event.accept()


if __name__ == "__main__":
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
    mainWin = OscilloscopeWindow()
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
