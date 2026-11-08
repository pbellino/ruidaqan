import pprint
import nidaqmx
import numpy as np
from nidaqmx.constants import AcquisitionType
from nidaqmx.stream_readers import ( AnalogMultiChannelReader,
                                     AnalogUnscaledReader,
                                   )
from pyqtgraph.Qt import QtCore
from .data_io import DataWriter


class GetDevicesInfo():
    """
    Obtiene información sobre la placa de adquisición de NI

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
        _system = nidaqmx.system.System.local()
        self.dev_names = _system.devices.device_names

    def device_info(self, dev_name="Dev1"):
        return self._device_info(dev_name)

    class _device_info():
        def __init__(self, dev_name):
            device = nidaqmx.system.device.Device(dev_name)
            # Convierto la lista que devuelve nidaqmx en una lista de tuplas 
            # con los rangos [(-10, 10), (-5, 5), ...]
            _rng_lst = device.ai_voltage_rngs
            self.ai_ranges = []
            for i in range(0, len(_rng_lst), 2):
                self.ai_ranges.append((_rng_lst[i], _rng_lst[i +1 ]))

            self.channel_names = device.ai_physical_chans.channel_names
            self.resolution_ADC = int(self._resolution_ADC(dev_name))

        def scaling_coeff(self, ai_channel_name="Dev1/ai0", ai_range=(-10, 10)):
            with nidaqmx.Task() as ni_task:
                ai_args = {'min_val': ai_range[0],
                           'max_val': ai_range[1]}
                ai_chan = ni_task.ai_channels.add_ai_voltage_chan(
                                    ai_channel_name, **ai_args)
                return ai_chan.ai_dev_scaling_coeff

        def _resolution_ADC(self, dev_name):
            with nidaqmx.Task() as ni_task:
                res = ni_task.ai_channels.add_ai_voltage_chan(
                                              dev_name + '/ai0').ai_resolution
            return res


class SignalReader(QtCore.QThread):
    """
    Thread for capturing input signal through DAQ

    TODO: Add reset device.

    Parameters
    ----------
        sample_rate : float
            Frecuencia de muestreo
        sample_size : float
            Cantidad de puntos a leer
        channels: list
            Canales a medir
        ranges: list of tuples
            (v_min, V_max) de cada canal a medir
        kargs:
            reading_type: string: "float"(default), "int16"
                Tipo de dato que se va a leer
            terminal_cfg: string: "RSE" (default), "NRSE"
                Tipo de conexión para los canales (se usa la misma para todos)

    """

    # Signal with read data
    incoming_data = QtCore.pyqtSignal(object)
    # Señal con el mensaje de error si la adquisición se interrumpe
    acquisition_error = QtCore.pyqtSignal(str)

    def __init__(self, sample_rate, sample_size, channels, ranges, **kargs):
        super().__init__()

        self.reading_type = kargs.get('reading_type', 'float')
        ter_cfg_val = kargs.get('terminal_cfg', 'RSE')
        # Cantidad de historias que se van a adquirir
        self.max_histories = kargs.get('max_histories', None)
        # Contador de historias adquiridas
        self.num_histories = 0
        ter_cfg_dic = {
                        'RSE': nidaqmx.constants.TerminalConfiguration.RSE,
                        'NRSE': nidaqmx.constants.TerminalConfiguration.NRSE,
                      }
        self.terminal_config = ter_cfg_dic[ter_cfg_val]

        self.reader = None
        self.is_running = False
        self.is_paused = False
        self.input_channels = channels
        self.input_ranges = ranges

        self.sample_rate = sample_rate
        self.sample_size = sample_size
        # actual data received from the DAQ
        if self.reading_type == "float":
            self.input = np.empty(shape=(len(channels), self.sample_size),
                                  dtype=np.float64)
        elif self.reading_type == "int16":
            self.input = np.empty(shape=(len(channels), self.sample_size),
                                  dtype=np.int16)
        else:
            msg = "Tipo de lectura no reconocida. Opciones: 'float', 'int16' "
            raise ValueError(msg)


    def run(self):
        """ Start thread for data acuisition. Called by QThread.start() """

        self.is_running = True
        if not self.create_task():
            self.is_running = False
            self.acquisition_error.emit(
                "No se pudo configurar la tarea de adquisición en la placa.")
            return None

        while self.is_running:
            if not self.is_paused:
                try:
                    # Read data acquiered
                    if self.reading_type == "float":
                        self.reader.read_many_sample(
                                 data=self.input,
                                 number_of_samples_per_channel=self.sample_size,
                                 timeout=-1,
                                )
                    elif self.reading_type == "int16":
                        self.reader.read_int16(
                                 data=self.input,
                                 number_of_samples_per_channel=self.sample_size
                                )
                    self.num_histories += 1
                    # Se emite una COPIA: el buffer self.input se reutiliza
                    # en la próxima lectura, y el slot que recibe los datos
                    # corre en el hilo del GUI (conexión encolada). Si se
                    # emitiera self.input, una lectura posterior podría
                    # sobrescribirlo antes de que el GUI lo copie.
                    self.incoming_data.emit(self.input.copy())
                    # Print data to screen
                    # pprint.pprint(self.input.T)
                    print("Total data acquired:"
                         f"{self.task.in_stream.total_samp_per_chan_acquired}")
                except Exception as e:
                    print("Error with read_many_sample")
                    print(e)
                    self.acquisition_error.emit(
                        "La adquisición se interrumpió después de "
                        f"{self.num_histories} historias.\n\n{e}")
                    break
            if self.num_histories == self.max_histories:
                # Se finaliza la adquisición al completar todas las historias
                break
        # Stops acquisition
        self.task.close()
        # Returns run and the thread is closed
        return None

    def create_task(self):
        """ Configura e inicia la tarea. Devuelve False si falla """
        try:
            self.task = nidaqmx.Task("Reader Task")
        except OSError:
            print("DAQ is not connected, task could not be created")
            return False

        try:
            for ch, rg in zip(self.input_channels, self.input_ranges):
                chan_args = {
                                'min_val': rg[0],
                                'max_val': rg[1],
                                'terminal_config': self.terminal_config,
                            }
                self.task.ai_channels.add_ai_voltage_chan(ch, **chan_args)
        except Exception as e:
            print("DAQ is not connected, channel could not be added")
            print(e)
            self.task.close()
            return False

        # Timing definition
        self.task.timing.cfg_samp_clk_timing(
            rate=self.sample_rate, sample_mode=AcquisitionType.CONTINUOUS
        )
        self.task.start()
        # Start acquisition
        if self.reading_type == "float":
            self.reader = AnalogMultiChannelReader(self.task.in_stream)
        elif self.reading_type == "int16":
            self.reader = AnalogUnscaledReader(self.task.in_stream)
        return True

    def restart(self):
        print("Restarting the task")
        # Closing
        self.is_paused = True
        self.task.stop()
        self.task.close()
        # self.writer.close_file()
        # Starting
        # self.writer = DataWriter()
        self.create_task()
        self.is_paused = False


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
