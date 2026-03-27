"""
Módulos para la lectura, procesamiento y análisis de los archivos con datos.

Se pueden leer los datos grabados tanto con la adquisición de RuiDAQAn como así
tamibén con los archivos .RUI grabados por el FERCIN3.

"""

from .data_fercin3_io import HDF5FileProcessing, \
                             RUIFileProcessing, \
                             FitResults

