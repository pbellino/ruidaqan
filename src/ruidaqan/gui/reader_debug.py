import pprint
import numpy as np
import time
from pyqtgraph.Qt import QtCore
from .data_io import DataWriter


class GetDevicesInfo():
    """
    Simula información sobre la placa de adquisición de NI

    dev_names : Lista con todos los dispositivos instalados en el sistema

    device_info(dev_name) : método para obtener información de un dispositivo
    específico

    device_info(dev_name).ai_ranges : Lista con rangos disponibles

    device_info(dev_name).channel_names : Lista con los nombres de canales
    disponibles

    device_info(dev_name).scaling_coeff(ai_channel_name, ai_range):
    coeficientes para convertir a voltage para un dado canal y un dado rango.
    Si bien por default son los mismos para todos los canales, se podrían
    configurar de forma individual.

    """
    def __init__(self):
        self.dev_names = [f"Dev{i}" for i in range(1, 4)]

    def device_info(self, dev_name="Dev1"):
        return self._device_info(dev_name)

    class _device_info():
        def __init__(self, dev_name):
            if dev_name == "Dev1":
                _rgs_lst = [-0.1, 0.1, -1, 1, -2, 2, -5, 5, -10, 10]
            else:
                _rgs_lst = [-0.1, 0.1, -1, 1, -2, 2, -4, 4]
            self.ai_ranges = []
            for i in range(0, len(_rgs_lst), 2):
                self.ai_ranges.append( (_rgs_lst[i], _rgs_lst[i +1]))

            self.channel_names = [f"{dev_name}/ai{i}" for i in range(12)]
            self.resolution_ADC = 16 if dev_name=="Dev1" else 12

        def scaling_coeff(self, ai_channel_name="Dev1/ai0", ai_range=(-1, 1)):
            if ai_channel_name == "Dev1/ai0":
                if ai_range == (-10, 10):
                    _co = [10, 0.2, 0.3]
                elif ai_range == (-5, 5):
                    _co = [5, 0.2, 0.3]
                elif ai_range == (-2, 2):
                    _co = [2, 0.2, 0.3]
                elif ai_range == (-1, 1):
                    _co = [1, 0.2, 0.3]
                else:
                    _co = [0, -0.1, 0.3]
            elif ai_channel_name == "Dev2/ai0":
                _co = [1, 1.2, 1.3]
            elif ai_channel_name == "Dev1/ai1":
                _co = [11, 11, 11]
            elif ai_channel_name == "Dev1/ai2":
                _co = [21, 21, 21]
            elif ai_channel_name == "Dev1/ai3":
                _co = [31, 31, 31]
            elif ai_channel_name == "Dev1/ai4":
                _co = [41, 41, 41]
            elif ai_channel_name == "Dev1/ai5":
                _co = [51, 51, 51]
            else:
                _co = [0, 1, 2]
            return _co


class SignalReader(QtCore.QThread):
    """
    Thread for simulating a signal

    """

    # Signal with read data
    incoming_data = QtCore.pyqtSignal(object)

    def __init__(self, sample_rate, sample_size, channels, *args, **kargs):
        super().__init__()

        self.reading_type = kargs.get('reading_type', 'float')

        self.reader = None
        self.is_running = False
        self.is_paused = False
        self.input_channels = channels

        self.sample_rate = sample_rate
        self.sample_size = sample_size


    def run(self):
        """ Start thread for data simulation. Called by QThread.start() """

        # self.writer = DataWriter()

        self.is_running = True
        while self.is_running:
            if not self.is_paused:
                rng = np.random.default_rng()
                if self.reading_type == "float":
                    # Simulate voltage data
                    self.input = rng.normal(0, 0.1,
                            size=(len(self.input_channels), self.sample_size)
                            )
                    # Add different offset for each cchannel
                    for i, _ in enumerate(self.input):
                        self.input[i, :] += i
                else:
                    # Simulate integer data
                    self.input = rng.poisson(10,
                            size=(len(self.input_channels), self.sample_size)
                            )
                    # Add different offset for each cchannel
                    for i, _ in enumerate(self.input):
                        self.input[i, :] += i
                    # Canal 0 saturado
                    # self.input[0, :] = 32767
                # Emit signal with the data
                self.incoming_data.emit(self.input)
                # Write data to file
                # self.writer.write_data(self.input)
                # Print data to screen
                # pprint.pprint(self.input.T)
                # Wait the time it would have taken to acquiere the real signal
                _time_acq = self.sample_size / self.sample_rate
                time.sleep(_time_acq)
        # Finish data writer
        # self.writer.close_file()
        # Returns run and the thread is closed
        return None


    def restart(self):
        print("Restarting the task")
        self.is_paused = True
        #self.writer.close_file()
        self.is_paused = False
        # self.writer = DataWriter()


if __name__ == "__main__":
    print("\nRunning demo for SignalReader\n")

    reader_thread = SignalReader(sample_rate=1000,
                                 sample_size=1000,
                                 channels=[0, 1, 2],
                                 dev_name='Dev1',
                                 )
    reader_thread.start()
    input("Press return to stop")
    reader_thread.is_running = False
    # Wait for the thread to finish (see QThread class)
    reader_thread.wait()
    print("\nTask done")
