import tables as tb
import numpy as np

"""
Script para modificar la corriente de fondo en varios archivos hdf5

"""

# Se completa cada detector cuya corriente de fondo se
# quiera modificar (comentar la que no se use)
corrientes_fondo = {}
corrientes_fondo['Cadena_1'] = [2.0, 0.2]
# corrientes_fondo['Cadena_2'] = [3.0, 0.3]
# corrientes_fondo['Cadena_Ip'] = [4.0, 0.4]

# Archivos cuyas corriente de fondo se desean modificar
archivos = [
            'S001-N1-1.h5',
            #'S001-N1-2.h5',
           ]

for archivo in archivos:
    with tb.open_file(archivo, mode='r+') as f:
        for cadena, corriente in corrientes_fondo.items():
            bb = f.get_node("/" + cadena)
            bb._v_attrs.Fondo = np.asarray(corriente)


