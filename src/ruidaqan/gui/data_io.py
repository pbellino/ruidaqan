import os
import numpy as np
from datetime import datetime
import tables as tb
from .misc_functions import weighted_average, int_to_volt


class DataWriter():
    """
    Write data to file
    """

    def __init__(self, filename="Output_Data.dat"):
        super().__init__()

        if os.path.exists(filename):
            f = open(filename, 'w')
            f.close()
        self._file = open(filename, 'a')

        self._file.write("# I am the header\n")

    def write_data(self, incoming_data):
        np.savetxt(self._file, incoming_data.T)

    def close_file(self):
        self._file.close()


def write_RUI_file(filename, data, cfg_gral, cfg_adv, cfg_meas, cip_manual=None):
    """
    Escribe un archivo con el formato .RUI del FERCIN3

    Sólo para comparar programas de procesamiento

    Se asume una tarjeta con 16 bits de resolución

    """
    now_date = datetime.now()
    now_time = datetime.now().time()

    # Carpeta donde se guardan y leen los datos
    data_folder = os.path.dirname(filename)

    cip = cfg_gral.get_param_value("Parámetros generales", "Medición de CIp")
    n_det = cfg_gral.get_param_value("Parámetros generales",
                                     "Cadenas de medición")
    fs = 2*cfg_meas.get_param_value("Parámetros medición", "DAQ", "BW manual")
    comments_cad = cfg_meas.get_comments()
    offsets = cfg_meas.get_offsets()
    sensitivities = np.asarray(cfg_meas.get_sensitivities())
    Z_cad = 1.0 / sensitivities
    ac_gains = cfg_meas.get_AC_gains()

    indx_ac = list(range(0, n_det * 3, 3))
    # Canales
    channels = cfg_adv.get_channels()
    # Rangos
    ranges = cfg_adv.get_channels_ranges()
    coefs = cfg_adv.get_channels_coefs(channels, ranges)
    rangos_ac = np.asarray(ranges)[indx_ac]

    data_volts = int_to_volt(data, coefs)

    # Datos con las DC's
    dc_indx = list(range(1, n_det*3, 3))
    dc_data_volts = data_volts[dc_indx, :]
    mean_dc = np.mean(dc_data_volts, axis=1)
    std_dc = np.std(dc_data_volts, ddof=1, axis=1)

    # Datos de corriente de Ip
    if cip:
        # Se usan los datos adquiridos
        # Se resta offset
        mean_Ip = np.mean(data_volts[n_det * 3, :]) - offsets[-1]
        # Se multiplica por la sensibilidad
        mean_Ip *= sensitivities[-1]
        std_Ip = np.std(data_volts[n_det * 3, :], ddof=1) * sensitivities[-1]
    else:
        # Se usan los datos ingresados a mano
        ip_data = np.asarray(cip_manual)
        print(f"En .RUI: {ip_data}")
        # Sólo valores con incerteza positiva (con incerteza nula el peso es
        # infinito y el promedio da NaN). La ventana de ingreso ya no los
        # acepta, pero pueden venir de un archivo de recuperación anterior.
        _ok = np.isfinite(ip_data[:, 0]) & (ip_data[:, 1] > 0)
        if _ok.any():
            mean_Ip, std_Ip = weighted_average(ip_data[_ok, 0],
                                               1 / ip_data[_ok, 1]**2)
        else:
            mean_Ip, std_Ip = np.mean(ip_data[:, 0]), np.nan
        print(f"En .RUI promediado: {mean_Ip} +/- {std_Ip}")

    # TODO: no hardcodear rango
    # Se debe sumar 2^16 / 2 para llevarlo a [0, 2^16 - 1]
    if n_det == 2:
        # Datos entrelazados de las AC's
        ac_data = np.empty(2 * data.shape[1], dtype=int)
        ac_data[0::2] = data[0, :] + 2**15
        ac_data[1::2] = data[3, :] + 2**15
    elif n_det == 1:
        ac_data = data[0, :] + 2**15

    # Fecha
    header  = '"' + now_date.strftime("%d-%m-%Y") + '"\n'
    # Hora
    header += '"' + now_time.strftime("%H:%M:%S") + '"\n'
    # Cantidad de datos AC
    header += f"{len(ac_data):.1f}\n"
    # dt        mean(Ip)    std(Ip)
    header += f"  {1/fs:.14f}  {mean_Ip:.14f}  {std_Ip:.14f}\n"
    # Cantidad de detectores
    header += f"{n_det}\n"
    # Tiempo muerto
    header += "0.0\n"
    for rango_ac in rangos_ac:
        # Rangos DAQ
        header += f"{rango_ac[1]}\n"
    names = [os.path.join(data_folder, s) for s in ("FONDO1", "FONDO2")]
    for i in range(n_det):
       # Comentario cadenas
       header += f'"{comments_cad[i]}"\n'
       mean_fdo, std_fdo = read_RUI_background(names[i])
       # mean(DC)-offset(DC)    std(DC)    mean(fondo)   std(fondo)
       header += ( f"  {mean_dc[i]-offsets[i]:.14f}  {std_dc[i]:.14f}"
                   f"  {mean_fdo:.14f}  {std_fdo:.14f}\n"
                 )
       # inversa sensibilidad y su incerteza
       header += f"     {Z_cad[i]:.2f}     {Z_cad[i]*0.01:.2f}\n"
       # ganancia AC y su incerteza
       header += f"     {ac_gains[i]:.2f}    {ac_gains[i]*0.01:.2f}\n"
    # Quito el último salto de línea
    header = header[:-1]
    # Escribe los datos de AC
    np.savetxt(filename, ac_data.T, fmt="%.i", header=header, comments="",
               encoding="utf-8")


def read_RUI_background(filename):
    try:
        mean_I, std_I = np.loadtxt(filename, delimiter=",", unpack=True)
    except IOError:
        mean_I, std_I = 0.0, 0.0
        print(f"No existe archivo {filename} con la corriente de fondo")
    return mean_I, std_I


def write_RUI_background(names, mean_datas, std_datas):
    """
    Graba los resultados de la medición de fondo en el formato del FERCIN3
    """
    for name, mean, std in zip(names, mean_datas, std_datas):
        with open(name, 'w', encoding="utf-8") as f:
            f.write(f"{mean:.6E},{std:.6E}")
        print(f"Se grabó el archivo {name}")


def write_background(filename, mean_datas, std_datas):
    with open(filename, "w", encoding="utf-8") as f:
        f.write("# Archivo temporal con las corrientes de fondo\n")
        f.write("# I1    I1_std\n")
        f.write("# ...   ...\n")
        f.write("# Ip    Ip_std\n")
        for mean, std in zip(mean_datas, std_datas):
            f.write(f"{mean:.6E}\t{std:.6E}\n")


def nombre_archivo_rui(output_file_HDF):
    """
    Nombre del .RUI a partir del .h5 de la medición: se quita un cero al
    comienzo de la serie (S010-N1-1.h5 -> S10-N1-1.RUI, formato de los
    programas de DOS) y se cambia la extensión. Sólo se modifica el nombre:
    la carpeta puede contener "S0" o ".h5".
    """
    carpeta, nombre = os.path.split(output_file_HDF)
    if nombre.startswith("S0"):
        nombre = "S" + nombre[2:]
    nombre = os.path.splitext(nombre)[0] + ".RUI"
    return os.path.join(carpeta, nombre)


class FondoIncompatible(ValueError):
    """ El archivo de fondo no corresponde a la configuración actual """


def read_background(filename):
    """
    Lee archivo con las corrientes de fondo (nuevo formato)

    Devuelve un array de dos dimensiones (una fila por cadena, con valor e
    incerteza) o None si el archivo no existe. Con ndmin=2, un archivo de una
    sola fila (un detector sin CIp) da shape (1, 2) y no (2,).
    """
    try:
        fondo = np.loadtxt(filename, delimiter="\t", unpack=False, ndmin=2)
    except IOError:
        fondo = None
        print(f"No existe archivo {filename} con la corriente de fondo")
    return fondo


def fondo_para_medicion(filename, n_det):
    """
    Corrientes de fondo para una medición con n_det cadenas.

    El archivo SXXX-FONDOS tiene una fila por cadena de medición y, si se
    adquirió la CIp durante la medición de fondo, una última fila para Ip.

    Returns
    -------
        fondo: array (n_det + 1, 2)
            Filas 0..n_det-1 para cada cadena y la última para Ip (nula si no
            se midió). Si no existe el archivo, todas nulas.

    Raises
    ------
        FondoIncompatible
            Si el archivo no tiene n_det ni n_det + 1 filas de dos columnas
            (p. ej. el fondo se midió con otra cantidad de cadenas).
    """
    fondo = read_background(filename)
    if fondo is None:
        return np.zeros((n_det + 1, 2))
    filas = fondo.shape[0] if fondo.size else 0
    if fondo.size and fondo.shape[1] == 2:
        if filas == n_det:
            return np.vstack([fondo, [[0.0, 0.0]]])
        if filas == n_det + 1:
            return fondo
    raise FondoIncompatible(
        f"El archivo de fondo {os.path.basename(filename)} tiene {filas} "
        f"fila(s), pero la configuración actual tiene {n_det} cadena(s) de "
        f"medición (se esperaban {n_det} o {n_det + 1} filas, contando la "
        "de Ip).\n\nProbablemente el fondo se midió con otra configuración. "
        "Volvé a medir el fondo con la configuración actual, o renombrá el "
        "archivo para medir sin fondo (corrientes de fondo nulas).")


class WriteHDF5File():
    """
    Clase para escribir datos de mediciónen nuevo formato
    """

    def __init__(self, filename, cfg_gral, cfg_adv, cfg_meas):
        self.filename = filename

        self.n_det = cfg_gral.get_param_value("Parámetros generales",
                                              "Cadenas de medición")
        self.cip = cfg_gral.get_param_value("Parámetros generales",
                                            "Medición de CIp")
        self.serie = cfg_gral.get_param_value( "Parámetros generales", "Serie")

        self.res_ADC = cfg_adv.get_ADC_resolution()
        self.ranges = cfg_adv.get_channels_ranges()
        self.canales = cfg_adv.get_channels()
        self.coefs = cfg_adv.get_channels_coefs(self.canales, self.ranges)
        self.nombres = cfg_adv.get_channels_labels()

        self.offsets = cfg_meas.get_offsets()
        self.ac_gains = cfg_meas.get_AC_gains()
        self.sensitivities = cfg_meas.get_sensitivities()

        # Nombre del archivo con las corrientes de fondo
        # Carpeta donde se guardan y leen los datos
        data_folder = os.path.dirname(filename)
        background_filename = os.path.join(data_folder,
                                                   f"S{self.serie:03d}-FONDOS")
        # Lee el archivo con las corrientes de fondo: una fila por cadena y
        # la última para Ip (nula si no se midió). Se valida antes de crear
        # el archivo HDF5; si no corresponde a la configuración actual se
        # lanza FondoIncompatible.
        fondo = fondo_para_medicion(background_filename, self.n_det)

        # Se abre el archivo donde se escribirán los datos
        h5file = tb.open_file(self.filename, mode='w')

        # --- Para cada detector
        empty_array = np.asarray([], dtype=np.int16)
        for i in range(self.n_det):
            g = h5file.create_group("/", f"Cadena_{i+1}")
            # Atributos de la cadena
            g._v_attrs.Offset = self.offsets[i]
            g._v_attrs.AC_gains = self.ac_gains[i]
            g._v_attrs.Sensibilidad = self.sensitivities[i]
            g._v_attrs.Fondo = fondo[i, :]
            for k, tipo in enumerate(["AC", "DC"]):
                # Arrays para DC y AC de cada detector
                ar = h5file.create_earray(g, tipo, obj=empty_array)
                # Atributos de cada canal
                ar.attrs.Coeficientes = np.asarray(self.coefs[3 * i + k],
                                                             dtype=np.float64)
                ar.attrs.Rango = np.asarray(self.ranges[3 * i + k],
                                                             dtype=np.float64)
                ar.attrs.Canal = self.canales[3 * i + k]
                ar.attrs.Nombre = self.nombres[3 * i + k]

        # ---- Para los datos de Ip
        g = h5file.create_group("/", "Cadena_Ip")
        # Fondo si existe
        g._v_attrs.Fondo = fondo[-1, :]
        # Distingo si se adquirió o se ingresaron manualmente
        if self.cip:
            # ATributos de la cadena
            g._v_attrs.Offset = self.offsets[-1]
            g._v_attrs.Sensibilidad = self.sensitivities[-1]

            # Adquiridos, se graban como int16
            ar = h5file.create_earray(g, "DC", obj=empty_array)
            # Atributos del canal
            ar.attrs.Coeficientes = np.asarray(self.coefs[3 * self.n_det ],
                                                             dtype=np.float64)
            ar.attrs.Rango = np.asarray(self.ranges[3 * self.n_det ],
                                                             dtype=np.float64)
            ar.attrs.Canal = self.canales[3 * self.n_det]
            ar.attrs.Nombre = self.nombres[3 * self.n_det]
        else:
            # Manuales, se graban ls floats ingresados con sus incertezas
            empty_array_float = np.asarray([], dtype=np.float64)
            h5file.create_earray(g, "DC_mag", obj=empty_array_float,
                                 title="Corriente")
            h5file.create_earray(g, "DC_std", obj=empty_array_float,
                                 title="Desvio estándar corriente")

        # ---- Atributos para el archivo
        now_date = datetime.now()
        now_time = datetime.now().time()
        h5file.root._v_attrs.Fecha = now_date.strftime("%d-%m-%Y")
        h5file.root._v_attrs.Hora = now_time.strftime("%H:%M:%S")

        h5file.root._v_attrs.Reactor = cfg_gral.get_param_value(
                                        "Parámetros generales", "Reactor")
        h5file.root._v_attrs.Nucleo = cfg_gral.get_param_value(
                                        "Parámetros generales", "Núcleo")
        h5file.root._v_attrs.Serie = self.serie
        h5file.root._v_attrs.N_detectores = self.n_det
        h5file.root._v_attrs.CIp_adquirido = self.cip
        h5file.root._v_attrs.Comentario = cfg_gral.get_param_value(
                                         "Parámetros generales", "Comentarios")

        h5file.root._v_attrs.Nivel = cfg_meas.get_param_value(
                                    "Parámetros medición", "Medición", "Nivel")
        h5file.root._v_attrs.Medicion = cfg_meas.get_param_value(
                                 "Parámetros medición", "Medición", "Medición")
        h5file.root._v_attrs.Comentario_medicion = cfg_meas.get_param_value(
                               "Parámetros medición", "Medición", "Comentario")
        h5file.root._v_attrs.BW = cfg_meas.get_param_value(
                               "Parámetros medición", "DAQ", "BW manual")
        h5file.root._v_attrs.N_puntos = cfg_meas.get_param_value(
                               "Parámetros medición", "DAQ", "Puntos")
        h5file.root._v_attrs.Historias = cfg_meas.get_param_value(
                               "Parámetros medición", "DAQ", "Historias")

        h5file.root._v_attrs.Resolucion_DAC = self.res_ADC

        h5file.close()


    def append_new_data(self, new_data, cip_data=None):
        """
        Método para agregar datos durante la adquisición

        """
        h5file = tb.open_file(self.filename, mode='a')
        # Graba datos detectores
        for i in range(self.n_det):
            for k, tipo in enumerate(["AC", "DC"]):
                node = h5file.get_node(f"/Cadena_{i+1}", tipo)
                node.append(new_data[3 * i + k, :])
        # Graba datos Ip adquiridos
        if self.cip:
            node = h5file.get_node("/Cadena_Ip", "DC")
            node.append(new_data[3 * self.n_det, :])

        h5file.close()


    def append_manual_cip(self, cip_manual):
        """
        Guarda los datos de Ip ingresados de forma manual
        """
        ip_data = np.asarray(cip_manual)

        h5file = tb.open_file(self.filename, mode='a')

        node = h5file.get_node("/Cadena_Ip", "DC_mag")
        node.append(ip_data[:, 0])
        node = h5file.get_node("/Cadena_Ip", "DC_std")
        node.append(ip_data[:, 1])

        h5file.close()

