#! /usr/bin/env python3

import numpy as np
import tables as tb

"""
    Script para comparar que los valores guardados en .RUI y hdf5 coincidan
"""

if __name__ == "__main__":
    # Archivos que se van a comparar
    file_rui = "S00-N1-1.RUI"
    file_hdf5 = "S000-N1-1.h5"

    # Lectura de .RUI
    data = np.loadtxt(file_rui, skiprows=16)
    ac_1 = data[0::2] - 2**15
    ac_2 = data[1::2] - 2**15

    # Lectura de HDF5
    with tb.open_file(file_hdf5, mode='r') as f:
        ach_1 = f.get_node(f"/Cadena_1").AC.read()
        ach_2 = f.get_node(f"/Cadena_2").AC.read()

    # Comparación
    print(80*'-')
    print(len(ac_1), len(ach_1))
    print(np.asarray([ac_1, ach_1]).T)
    print(80*'-')
    print(len(ac_2), len(ach_2))
    print(np.asarray([ac_2, ach_2]).T)
    print(f"AC1 son iguales: {all(ac_1 == ach_1)}")
    print(f"AC2 son iguales: {all(ac_2 == ach_2)}")
