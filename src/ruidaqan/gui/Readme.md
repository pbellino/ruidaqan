# Programa de adquisición para ruido neutrónico

## Características

* Programado en python 3.8 usando el módulo pyqt (implementación de qt5 para python)

* El programa es multiplataforma (Windows y Linux) pero los drivers de NI sólo están para Windows

* Se están probando en una máquina virtual con Windows10 y Anaconda y los API's oficiales de los drivers de NI

* Adquisición de señales analógicas

* Libertad para elegir la cantidad de cadenas de medición utilizadas

* Libertad par elegir cualquier tarjeta de NI disponible

* Se adquieren tres señales por cada cadena de medición:

    - Componente AC luego del filtro anti-aliasing
    
    - Componente DC

    - Componente AC a la entrada del filtro anti-aliasing 

* Está pensado para trabajar con los equipos CNEA-K330 y CNEA-K331 (amplificaddor y filtro anti-aliasing), pero se da la libertad de incluir parámetros para cualquier otro equipo

* Se diseñó separando la adquisición del procesamiento (que aún falta hacerla la interfase gráfica)

* Como mínimo se buscó que tenga las mismas funcionalidades que el programa FERCIN3 escrito en QBASIC

* Opción para hacer un ajuste de rango automático

* Monitoreo de la utilización del rango de la tarjeta, se interrumpe la adquisición si hay saturación en más del 1% de los datos

    - La saturación se verifica sobre los int16, como la calibración no es lineal, por lo general son admitidos valores mayores al rango nominal.

* Monitoreo a la entrada del filtro anti-aliasing, se interrumpe la adquisición si hay más del 1% de los datos que superan los 4V (máximo voltaje de entrada del filtro)

    - La saturación se verifica sobre el voltaje. Se respetan los 4V.

* Las señales se adquieren en enteros de 16 bits (resolución de la tarjeta) y luego se pasan a voltaje con los coeficientes de calibración

* Visualización de las señales y espectros (falta) durante la medición

* Se graban datos en formato compatible con el FERCIN5 para su procesamiento (comparación y validación)

* Falta pensar un nuevo formato de archivo de salida que contenga todos los datos necesarios no incluidos en los archivos .RUI (coeficientes de calibración, resolución, señal DC, etc)


## Lógica sobre control de saturación:

Se probaron las siguientes situaciones:

    1) Saturación en los canales AC (rango fijo 5V)
    2) Saturación en los canales AC a la entrada del filtru antialiasing (4V)
    3) Saturación canales DC

Dependiendo del tipo de medición que se está haciendo, el control de saturació será distinto. La adquisición se detendrá cuando:

 * Ajuste de rango en la medición de fondo

    - (1) No se detiene
    - (2) No se detiene

 * Medición de fondo
    
    - (1) No se detiene
    - (2) No se detiene
    - (3) Sí se detiene

 * Ajuste de rango en la medición

    - (1) Sí se detiene
    - (2) Sí se detiene
    - (3) Sí se detiene

 * Medición

    - (1) Sí se detiene
    - (2) Sí se detiene
    - (3) Sí se detiene

## TODO

* Ver cómo incorporar la ganancia y su error en la estimación de parámetros (actualmente se usa valor nominal)

* Pensar una nueva forma de guardar datos y constantes para unificar el uso (todas las funciones transferencia separadas por carpetas)


