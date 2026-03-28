RuiDAQAn
========

===========  ==================================================================
Info         Adquisición y análisis de señales para la técnica de ruido 
             neutrónico
Author       División FER - CNEA
===========  ==================================================================

version = "0.1.7"

Acerca
======

El paquete **ruidaqan** contiene herramientas para la adquisición de datos,
procesamiento espectral de las señales y análsis de los resultados para una
calibración en potencia de un reactor nuclear.

Se puede utilizar tanto con las interfases gráficas, como así también 
importándolo como módulo para hacer procesamiento y análisis con scripts (no
se puede adquirir, por ahora, con un script).

Existen tres interfases gráficas en **ruidaqan** que pueden ser usadas de forma
independiente una de otra:

- Adquisición de señales

  Adquiere y muestra los espectros en tiempo real. Utiliza los API de 
  `nidaqmx <https://github.com/ni/nidaqmx-python>`_ y se puede utilizar con
  la mayoría de las DAQ de NI.
  
  En cuanto a la electrónica asociada, Está pensada para trabajar con un 
  los amplificadores CNEA-K330 y filtros antialiasing CNEA-K231.

- Procesamiento de datos

  Lee los archivos .RUI (los grabados por el FERCIN-3) y los archivos .h5 que
  genera la interfase gráfica de adquisición. Realiza los ajustes de los
  espectros y estima parámetros cinéticos.

- Resultados

  Pensada para ser utilizada durante una calibración en potencia. Lee los 
  resultados obtenidos del procesamiento de datos, y con ellos saca factores
  de calibración en potencia. Hace promedios sobre los parámetros cinéticos
  obtenidos durante cada medición durante la calibración.

Si se tienen que procesar y analizar muchos datos (típicamente todos los
archivos obtenidos en una calibración) resulta más conveniente importar a
**ruidaqan** como módulo y hacer uso de las clases disponibles para tal fin.


Instalación
===========

Se recomienda instalarlo dentro de un entorno virtual con python 3.10, aunque 
es algo optativo.

Es necesario tener instaladas las bibliotecas de
`HDF5 <https://www.hdfgroup.org>`_, ya que se utiliza ese formato para guardar
los datos adquiridos.


Usando el código fuente:
------------------------

- Bajar o clonar este repositorio
- En la carpeta raíz (donde se encuentra el archivo **pyproject.toml**):
    
    $ python -m pip install .

- Si se quiere modificar el código es conveniente instalarlo como:
    
    $ python -m pip install -e .

  de esta manera no es necesario volverlo a instalar cada vez que se hace un 
  cambio.


Usando el paquete wheel:
------------------------

- Bajar de la carpeta **dist/** el paquete que corresponde al SO deseado
- Dentro del entorno virtual:

    $ python -m pip install [NOMBRE_DEL_PAQUETE].whl

Uso
===

Se pueden llamar a las tres intefases gráficas de forma independiente. También 
se admite importar clases necesarias para el procesamiento y análisis de datos 
ya adquiridos.

Interfase gráfica:
------------------

Las interfases gráficas se pueden llamar con su nombre completo o con su 
nombre abreviado.

- Para abrir la ventana de adquisición de datos:

    $ ruidaqan adquisición

    $ ruidaqan a

  Cuando se llame a esta ventana se generará una carpeta `datos` en la 
  ubicación desde donde se ejecutó el comando anterior. En esa carpeta se 
  guardarán los datos adquiridos.


- Para abrir la ventana de análisis espectral y procesamiento:

    $ ruidaqan procesamiento

    $ ruidaqan p

- Para abrir la ventana de resultados y ajustes lineales:

    $ ruidaqan resultados

    $ ruidaqan r

Simulación de la adquisición
>>>>>>>>>>>>>>>>>>>>>>>>>>>>

El programa de adquisición hace uso del API para python de los drivers de NI 
(nidaqmx). Durante el desarrollo del programa es común que se trabaje en una 
computadora que puede no tener instalados dichos drivers. Por tal motivo, se 
agregó una opción para simular las señales adquiridas (todas las señales son 
realizaciones aleatorias de procesos Gaussianos).

Para habilitar esta opción, se debe definir como ``True`` a la variable de 
entorno ``RUIDAQAN_DEBUG_MODE``.

- En Linux:

    $ export RUIDAQAN_DEBUG_MODE=True

- En Windows, con cmd:

    $ set RUIDAQAN_DEBUG_MODE=True

- En Windows, con PowerShell:

    $ $env:RUIDAQAN_DEBUG_MODE="True"

Por default, si no se define esta variable, se toma como ``False``.
  

Como módulo:
------------

- Para abrir y procesar datos de archivos .h5 ya adquiridos:

.. code-block:: python

    >>> from ruidaqan.script import HDF5FileProcessing
    >>> from ruidaqan.constantes import RA3 as REACTOR
    >>> rui = HDF5FileProcessing("S001-N2-1.h5")
    >>> espectros, fs = rui.get_spectrums(512, 0)
    >>> norm_espectros, fs = rui.get_normalized_spectrums("RA3", freqs_to_remove=[50, 100, 150])
    >>> # Intervalos para el ajuste de los espectros
    >>> if rui.BW == 200:
    ...     intervalos = 2 * [(2.3, 178.9)] + [(2.3, 93)]
    ... elif rui.BW == 40:
    ...     intervalos = 3 * [(2.8, 35.8)]
    >>> rui.fit_spectrums(intervalos, plot=True)
    >>> rui.calcula_parametros_cineticos(REACTOR)


- Para abrir y analizar los resultados de los parámetros estimados durante una 
  calibración:

.. code-block:: python

    >>> from ruidaqan.script import FitResults
    >>> filename = "S001-resultados_ajustes.pkl"
    >>> fit_results = FitResults(filename)
    >>> fit_results.fit_p_vs_I()
    >>> for fps in fit_results.fited_p_vs_I:
    >>>     print(fps[0])
    >>> fit_results.fit_Ip_vs_I(plot=True)
    >>> fit_results.average_parameters(plot=True)


Documentación
=============

Licencia
========

Contribuidores
==============

- Pablo Bellino (pbellino@cnea.gov.ar)

