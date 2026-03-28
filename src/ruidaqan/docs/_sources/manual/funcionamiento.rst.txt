Funcionamiento
==============

Se describen aspectos específicos sobre cómo funciona internamente el programa.

Está pensado como complemento para el usuario y como ayuda para el desarrollo 
del programa.

Está dividido en tres secciones:

- **Adquisición**

  Aspectos relacionados con el proceso de adquisición y archivo de salida

- **Procesamiento**

  Aspectos sobre cómo se obtienen los espectros y cómo se hace el ajuste
  
- **Resultados**

  Aspectos sobre cómo se utilizan los datos obtenidos para realizar la 
  calibración en potencia.

Adquisición
------------

La adquisición de datos relacionada con la medición de ruido neutrónico se hace
leyendo los datos en enteros de 16 bits (ver ``SignalReader`` dentro de
``reader.py``. Esto se hace porque las tarjetas de adquisición utilizadas 
hasta el momento tienen dicha resolucón.

La conversión a voltaje se realiza a través de los coeficientes de conversión,
que son leidos del dispositivo (ver ``ai_dev_scaling_coeff`` de nidaqmx). 
Estos coeficientes quedan definidos una vez que se define el rango de trabajo 
del canal.

Los datos adquiridos se guardan tambén como enteros de 16 bits junto con los 
coeficientes de conversión. Por compatibilidad con el programa FERCIN3-VB 
también se guardan los coeficientes en un archivo aparte. Esto último será 
eliminado una vez completada la etapa de validación del programa.

Para el osciloscopio, por el contrario, la adquisicón se realiza directamente 
en voltaje (``read_many_samples`` de nidaqmx). De esta manera se puede 
comprobar si se está cometiendo algún error en durante las mediciones de ruido,
que se hace adquiriendo enteros (``read_int16`` de nidaqmx).

La adquisicón se realiza en bloques de datos (por default 512), que son 
procesados en tiempo real mientras se realiza la adquisicón.

Previo a cada medición el programa permite realizar un ajuste automático del 
rango de voltaje utilizado par la adquisición (ver `Ajuste de rangos`_). El 
objetivo es reducir el error asociado al proceso de digitalización de la señal 
analógica.

Durante la adquisicón también se realiza un control de la saturación para 
asegurar la confiabilidad de los datos medidos (ver `Control de saturación`_).


Ajuste de rangos
+++++++++++++++++

El algoritmo para selecionar el mejor rango consiste en: 

- Adquirir datos 
- Convertirlos a voltaje
- Encontrar el mayor valor (en módulo) y buscar el primer rango más grande que
  dicho valor 

La implementación se hio en el método ``select_ranges`` de 
``RangeAdjustmentWindow`` en ``acquisition_window.py``.

La adquisición se realiza tomando dos bloques de 512 datos, con una frecuencia 
de muestreo de 400 Hz.

En esta implementación se asumen que se trabaja con rangos bipolares (los 
únicos disponibles en las tarjetas NI probadas), aunque también debería
con rango unipolares (nunca fue probado).

El ajuste de rangos no se reliza para la señal adquirida a la entrada del
filtro anti-aliasing, ya que ésta no interviene directamenet en la medición. En
este caso el rango queda fijo en (-5, 5) volts (se asume que es un rango 
válido, de lo contrario se debe modificar el código). Aquí se está asumiendo
que se trabajará con el filtro anti-aliasing CNEA-K340, cuya entrada satura en
4V.

Al comienzo del ajuste se comienza con los rangos (-5, 5) volts para los 
canales que adquieren componentes fluctuantes, y con (-10, 10) volts para los 
canales que adquieren componentes contínuas. Estos rangos están hardcodeados, 
prestar atención si la tarjeta no posee dichos rangos ya que se debe modificar 
el código.


Control de saturación
++++++++++++++++++++++

Una vez comenzada la adquisiciín, el programa realiza una serie de controles 
para asegurar la validez de los datos registrados. Se realizan dos 
comprobaciónes independientes: que se trabaje dentro del rango especificado en 
todos los canales y que no se sature la entrada del filtro anti-aliasing.

En ambos casos se toma el criterio de acpetar una medición si menos del 1% del 
**total** de los puntos adquiridos no superan los valores máximos. El control 
se realiza en cada bloque adquirido, no se espera a que se termine la 
adquisición (tal como lo hacía el FERCIN3), de esta manera si ya se pasa el 1% 
de los datos totales, la adquisición se corta antes de finalizar todas las 
historias.

La implementación se hizo en la clase ``ProgresoMedicion`` en 
``procesado_gui.py``.

1. Control del rango de la tarjeta
   
   Se comprueba que todos los canales utilizados para la adquisicón estén 
   adquiriendo dentro de los límites del rango especificado.

   La comparación se hace sobre los datos adquiridos en enteros de 16 bits. Es 
   decir, que no se sobrepase el valor :math:`2^{16-1} -1` (para una ADC de 16 
   bits con rango bipolar). ESte criterio es más laxo que hacer la comprobación
   por voltaje, ya que usualmente las tarjetas permiten medir valores cercanos 
   por fuera del rango especificado.

   Durante la medición de fondo sólo se comprueba el rango para los canales que
   miden las componentes contínuas de las señales. No se hace sobre las 
   fluctuanes debido a que no intervienen en la medición de fondo.

   Implementado en el método ``check_saturation_ranges`` dentro de la clase
   ``ProgresoMedicion``.

2. Control a la entrada del filtro anti-aliasing

   Debido a que el filtro anti-aliasing CNEA-K340 posee una entrada que satura 
   en 4V, se controla que no se supere dicho valor.

   Se hace la comparación convirtiendo los datos adquiridos a voltaje.

   No se realiza este control durante la medición de fondo, ya que la 
   componente fluctuante no interviene en la medición. 

   Durante cada bloque adquirido se informa también el porcentaje del rango 
   utilizado, que luego se visualiza en distintas ventanasdel programa.

   Implementado en el método ``check_saturation_antialiasing`` dentro de la 
   clase ``ProgresoMedicion``.


Archivo de salida
+++++++++++++++++

El programa de aquisicón guarda los datos adquiridos por medición, junto con 
otra información relevante, en un archivo con formado HDF5. Este archivo luego 
es abierto por el programa de procesamiento.

Para poder realizar comparaciones con el programa FERCIN5 también se guardan 
los datos en el mismo formato que lo guarda el programa FERCIN3 (.RUI).

TODO: describir datos y atributus guardados en hdf5

Procesamiento
-------------

Corrección con la función transferencia
+++++++++++++++++++++++++++++++++++++++


Método espectral
++++++++++++++++


Ajuste del espectro
+++++++++++++++++++


Resultados
-----------
