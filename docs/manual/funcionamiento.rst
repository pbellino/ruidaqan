Funcionamiento
==============

Se describen aspectos específicos sobre cómo funciona internamente el programa.

Está pensado como complemento para el usuario y como ayuda para el desarrollo
del programa.

Está dividido en cuatro secciones:

- **Adquisición**

  Aspectos relacionados con el proceso de adquisición.

- **Archivos**

  Contenido de los archivos que genera y lee el programa.

- **Procesamiento**

  Cómo se obtienen los espectros, cómo se ajustan y cómo se calculan los
  parámetros y sus incertezas.

- **Resultados**

  Cómo se utilizan los datos obtenidos para realizar la calibración en
  potencia.

Adquisición
------------

La adquisición de datos relacionada con la medición de ruido neutrónico se hace
leyendo los datos en enteros de 16 bits (ver ``SignalReader`` dentro de
``reader.py``). Esto se hace porque las tarjetas de adquisición utilizadas
hasta el momento tienen dicha resolución.

La conversión a voltaje se realiza a través de los coeficientes de conversión,
que son leídos del dispositivo (ver ``ai_dev_scaling_coeff`` de nidaqmx).
Estos coeficientes quedan definidos una vez que se define el rango de trabajo
del canal.

Los datos adquiridos se guardan también como enteros de 16 bits junto con los
coeficientes de conversión. Por compatibilidad con el programa FERCIN3-VB
también se guardan los coeficientes en un archivo aparte. Esto último será
eliminado una vez completada la etapa de validación del programa.

Para el osciloscopio, por el contrario, la adquisición se realiza directamente
en voltaje (``read_many_samples`` de nidaqmx). De esta manera se puede
comprobar si se está cometiendo algún error durante las mediciones de ruido,
que se hacen adquiriendo enteros (``read_int16`` de nidaqmx).

La adquisición se realiza en bloques de datos (por defecto 512), que son
procesados en tiempo real mientras se realiza la adquisición.

Previo a cada medición el programa permite realizar un ajuste automático del
rango de voltaje utilizado para la adquisición (ver `Ajuste de rangos`_). El
objetivo es reducir el error asociado al proceso de digitalización de la señal
analógica.

Durante la adquisición también se realiza un control de la saturación para
asegurar la confiabilidad de los datos medidos (ver `Control de saturación`_).


Ajuste de rangos
+++++++++++++++++

El algoritmo para seleccionar el mejor rango consiste en:

- Adquirir datos con los rangos máximos
- Convertirlos a voltaje
- Encontrar el mayor valor (en módulo) de cada canal y elegir el menor rango
  de la tarjeta que sea mayor que dicho valor

La implementación se hizo en el método ``select_ranges`` de
``RangeAdjustmentWindow`` en ``acquisition_window.py``.

La adquisición se realiza tomando dos bloques de 512 datos, con una frecuencia
de muestreo de 400 Hz.

En esta implementación se asume que se trabaja con rangos bipolares (los
únicos disponibles en las tarjetas NI probadas), aunque también debería
funcionar con rangos unipolares (nunca fue probado).

El ajuste de rangos no se realiza para la señal adquirida a la entrada del
filtro anti-aliasing, ya que ésta no interviene directamente en la medición. En
este caso el rango queda fijo en (-5, 5) volts (se asume que es un rango
válido, de lo contrario se debe modificar el código). Aquí se está asumiendo
que se trabajará con el filtro anti-aliasing CNEA-K340, cuya entrada satura en
4 V.

Al comienzo del ajuste se comienza con los rangos (-5, 5) volts para los
canales que adquieren componentes fluctuantes, y con (-10, 10) volts para los
canales que adquieren componentes continuas. Estos rangos están fijos en el
código: prestar atención si la tarjeta no posee dichos rangos, ya que en ese
caso se debe modificar el código.

El porcentaje de utilización que se muestra después de ajustar es el del
rango ajustado.


Control de saturación
++++++++++++++++++++++

Una vez comenzada la adquisición, el programa realiza una serie de controles
para asegurar la validez de los datos registrados. Se realizan dos
comprobaciones independientes: que se trabaje dentro del rango especificado en
todos los canales y que no se sature la entrada del filtro anti-aliasing.

En ambos casos se acepta la medición si a lo sumo el 1 % del **total** de los
puntos que se adquirirán alcanza los valores máximos. El control se realiza en
cada bloque adquirido y no se espera a que termine la adquisición (como hacía
el FERCIN3): apenas los puntos saturados superan el 1 % del total, la
adquisición se corta, antes de completar todas las historias.

La implementación se hizo en la clase ``ProgresoMedicion`` en
``procesado_gui.py``.

1. Control del rango de la tarjeta

   Se comprueba que todos los canales utilizados para la adquisición estén
   adquiriendo dentro de los límites del rango especificado.

   La comparación se hace sobre los datos adquiridos en enteros de 16 bits. Es
   decir, que el valor absoluto no alcance :math:`2^{16-1} -1` (para una ADC
   de 16 bits con rango bipolar), de modo que se detecta la saturación en los
   dos extremos del rango. Este criterio es más laxo que hacer la comprobación
   por voltaje, ya que usualmente las tarjetas permiten medir valores cercanos
   por fuera del rango especificado.

   Durante la medición de fondo sólo se comprueba el rango para los canales que
   miden las componentes continuas de las señales. No se hace sobre las
   fluctuantes debido a que no intervienen en la medición de fondo.

   Implementado en el método ``check_saturation_ranges`` dentro de la clase
   ``ProgresoMedicion``.

2. Control a la entrada del filtro anti-aliasing

   Debido a que el filtro anti-aliasing CNEA-K340 posee una entrada que satura
   en 4 V, se controla que el valor absoluto de la señal no supere dicho valor
   (+4 V o -4 V).

   Se hace la comparación convirtiendo los datos adquiridos a voltaje.

   No se realiza este control durante la medición de fondo, ya que la
   componente fluctuante no interviene en la medición.

   Durante cada bloque adquirido se informa también el porcentaje del rango
   utilizado, que luego se visualiza en distintas ventanas del programa.

   Implementado en el método ``check_saturation_antialiasing`` dentro de la
   clase ``ProgresoMedicion``.


Archivos
--------

Todos los archivos de una serie se graban en la carpeta de trabajo (ver el
menú de la ventana principal en :doc:`pantallas`). ``XXX`` es la serie con
tres dígitos, ``Y`` el nivel y ``Z`` la medición.

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Archivo
     - Contenido
   * - ``SXXX-NY-Z.h5``
     - Medición (formato principal, ver abajo)
   * - ``SXX-NY-Z.RUI``
     - La misma medición en el formato del FERCIN3 (sin el primer cero de la
       serie: ``S010`` pasa a ``S10``)
   * - ``SXX-coeficientes_int_to_volt.pkl``
     - Coeficientes de conversión de enteros a voltaje de la tarjeta, para
       procesar los .RUI
   * - ``SXXX-FONDOS``
     - Corrientes de fondo de la serie
   * - ``FONDO1``, ``FONDO2``, ``FONDO-IP``
     - Corrientes de fondo en el formato del FERCIN3
   * - ``SXXX-resultados_ajustes.pkl``
     - Resultados de los ajustes de la serie (ver `Resultados`_)
   * - ``SXXX-NY-Z-ingresos_manuales_cip.pkl``
     - Valores de Ip ingresados a mano durante una medición. Se borra al
       finalizarla; si queda (porque el programa se cerró antes), se
       recuperan al repetir esa medición.


Archivo HDF5 de cada medición
+++++++++++++++++++++++++++++

Contiene los datos crudos (enteros de 16 bits) y todo lo necesario para
procesarlos. Se puede inspeccionar, por ejemplo, con ``h5ls -v`` o con
``tables.open_file`` de PyTables.

**Atributos de la raíz** (``/``)
    ``Fecha``, ``Hora``, ``Reactor``, ``Nucleo``, ``Serie``,
    ``N_detectores``, ``CIp_adquirido`` (si la Ip se adquirió con la tarjeta
    o se ingresó a mano), ``Comentario``, ``Nivel``, ``Medicion``,
    ``Comentario_medicion``, ``BW`` [Hz] (la frecuencia de muestreo es
    :math:`2\,BW`), ``N_puntos`` (puntos por historia), ``Historias`` y
    ``Resolucion_DAC`` [bits].

**Grupo** ``/Cadena_n`` (uno por cadena de medición)
    Atributos: ``Sensibilidad`` [A/V], ``Offset`` [V], ``AC_gains``
    (ganancia AC del amplificador) y ``Fondo`` (corriente de fondo y su
    incerteza [A]).

    Arrays ``AC`` y ``DC`` (enteros de 16 bits, todas las historias
    concatenadas), cada uno con los atributos ``Coeficientes`` (polinomio de
    conversión a voltaje), ``Rango`` [V], ``Canal`` y ``Nombre``. La señal a
    la entrada del filtro anti-aliasing sólo se usa para el control de
    saturación y no se graba.

**Grupo** ``/Cadena_Ip``
    Atributo ``Fondo``. Si la Ip se adquirió con la tarjeta: atributos
    ``Sensibilidad`` y ``Offset`` y array ``DC`` como en las cadenas. Si se
    ingresó a mano: arrays ``DC_mag`` y ``DC_std`` con los valores
    ingresados [A] y sus incertezas.

Las incertezas de la sensibilidad (1 %) y de la ganancia AC (0.5 %) no se
graban: las agrega el programa de procesamiento.


Corrientes de fondo
+++++++++++++++++++

``SXXX-FONDOS`` es un archivo de texto con una fila por cadena de medición y
una última fila para la Ip; cada fila tiene la corriente y su incerteza [A],
separadas por un tabulador. Se graba al terminar la medición de fondo y se lee
al comenzar cada medición de la serie: si su cantidad de filas no corresponde a
la cantidad de cadenas configurada, la medición no comienza y se avisa.


Procesamiento
-------------

La implementación está en la clase ``_ProcesamientoEspectral`` de
``data_fercin3_io.py``, de la que derivan ``HDF5FileProcessing`` y
``RUIFileProcessing``.

Método espectral
++++++++++++++++

Las densidades espectrales se estiman con el método de Welch
(``scipy.signal.welch`` y ``scipy.signal.csd``): la señal AC (en volts) de
cada cadena se divide en bloques de **Tamaño bloque** puntos, con
**Solapamiento** puntos en común entre bloques consecutivos, se multiplica cada
bloque por la **Ventana** elegida y se promedian los periodogramas de todos los
bloques. Se obtienen las APSD de cada cadena y, con dos cadenas, la CPSD
(``scipy.signal.csd`` estima :math:`\overline{X_1}\,X_2`).

Con ventana rectangular y sin solapamiento, los puntos del espectro son
prácticamente independientes y cada uno tiene la varianza del promedio de
:math:`K` periodogramas independientes, con :math:`K` la cantidad de bloques.
Con otra ventana o con solapamiento se usa el número equivalente de bloques
independientes

.. math::

    n_\text{eff} = \frac{K}{1 + 2 \sum_{j=1}^{K-1} (1 - j/K)\, \rho(j)^2}

donde :math:`\rho(j)` es la correlación de la ventana consigo misma desplazada
:math:`j` bloques [Welch (1967), IEEE Trans. Audio Electroacoust. 15(2),
70-73; Percival & Walden (1993), sec. 6.17]. Sin solapamiento
:math:`n_\text{eff} = K`.

Corrección con la función transferencia
+++++++++++++++++++++++++++++++++++++++

La función transferencia :math:`H(f)` de cada cadena (amplificador y filtro)
se lee de los archivos ``TR{K}{BW}A{n}.PSD`` generados por el programa
TRA.EXE, con :math:`K` la ganancia AC dividida por 100, :math:`BW` el ancho de
banda y :math:`n` la cadena, que están en
``ruidaqan/transferencias/<reactor>``. De cada archivo se obtienen
:math:`|H|^2` (cociente de las dos APSD, en dB) y :math:`H` (cociente entre la
CPSD y la APSD de entrada).

Los espectros corregidos y normalizados son

.. math::

    \text{NPSD}_i = \frac{\text{APSD}_i}{|H_i|^2\, V_i^2}, \qquad
    \text{NCPSD} = \frac{H_1\,\overline{H_2}\;\text{CPSD}}
                        {|H_1|^2\,|H_2|^2\; V_1 V_2}

donde :math:`V_i` es la tensión DC media de la cadena descontados el offset y
el fondo, :math:`V_i = \langle V_{DC} \rangle - V_\text{offset} - I_f/S`.

Si una función transferencia tiene menos puntos que el espectro, se usan los
puntos en común (y se avisa). Si no existe, no se puede procesar la medición.

**Frecuencia de línea.** En los espectros y en las funciones transferencia, los
puntos que están a menos de 1 Hz de :math:`f = f_l`, :math:`2 f_l` y
:math:`3 f_l` se reemplazan por el valor del último punto con frecuencia menor
o igual a :math:`f - 1` Hz.

Ajuste del espectro
+++++++++++++++++++

En el intervalo de frecuencias elegido se ajustan los modelos

.. math::

    \text{NPSD}(f) = \frac{A}{1 + (2\pi f/\alpha)^2} + C, \qquad
    \mathrm{Re}\,\text{NCPSD}(f) = \frac{A}{1 + (2\pi f/\alpha)^2}

con ``lmfit``. Con **Ajuste pesado** (por defecto) se usa mínimos cuadrados
pesados con la varianza del estimador de Welch [Bendat & Piersol, *Random
Data*, 4.ª ed. (2010), sec. 8.5]:

.. math::

    \mathrm{var}(\text{NPSD}) = \frac{\text{NPSD}^2}{n_\text{eff}}, \qquad
    \mathrm{var}(\mathrm{Re}\,\text{NCPSD}) =
    \frac{\text{NPSD}_1\,\text{NPSD}_2 + (\mathrm{Re}\,\text{NCPSD})^2}
         {2\,n_\text{eff}}

evaluadas con los modelos ajustados (se itera tres veces partiendo de un
ajuste sin pesos). Para la NCPSD se usan las NPSD ajustadas. Sin pesos, la
incerteza que informa el ajuste no tiene sentido estadístico: en una
simulación con los parámetros por defecto subestima la real en un factor 2 a
3.

A partir de los parámetros ajustados se calculan

.. math::

    P = \frac{2\, E_f\, D\, (1-\beta)\, L}{\beta^2 A}, \qquad
    f_q = \frac{C\, I}{2}, \qquad
    \frac{\varepsilon}{\beta^2} = \frac{A\, B}{(1-\beta)\, L\, D\, C}

con :math:`E_f` la energía por fisión, :math:`D` el factor de Diven,
:math:`L` el factor de forma, :math:`\beta` la fracción efectiva de neutrones
retardados, :math:`B` el factor de Bennett e :math:`I` la corriente media de
la cadena (sin fondo), todos leídos de ``constantes_reactores.py`` salvo
:math:`I`. :math:`f_q` y :math:`\varepsilon/\beta^2` sólo se calculan con las
NPSD (necesitan :math:`C`). Las incertezas se propagan con la matriz de
covarianza del ajuste (paquete ``uncertainties``).

Incerteza por lotes
+++++++++++++++++++

Para comprobar la incerteza del ajuste, la señal se divide en :math:`J`
tramos consecutivos (:math:`J = \min(10, K/5)`), en cada tramo se repite todo
el procesamiento y la incerteza de la potencia por lotes es
:math:`u_\text{lotes} = s/\sqrt{J}`, con :math:`s` el desvío estándar de las
:math:`J` potencias. Si la incerteza del ajuste es correcta,

.. math::

    T = (J - 1) \left(\frac{u_\text{lotes}}{u_\text{ajuste}}\right)^2
    \sim \chi^2(J - 1)

Si el valor :math:`p` de la cola superior es menor que 0.01, se informa la
incerteza por lotes (la medición se marca); si no, la del ajuste. El test se
aplica sólo a la potencia: en simulaciones con mediciones estacionarias, para
:math:`\alpha` la dispersión entre tramos supera sistemáticamente la que
predice el ajuste (rechazos del 3 al 5 % con un nivel nominal del 1 %), por lo
que el test no es válido para :math:`\alpha`.


Resultados
-----------

``SXXX-resultados_ajustes.pkl`` guarda una tabla (array de numpy de objetos)
con una fila por espectro y las columnas

    Nivel, Medición, BW, Espectro (``NPSD1``, ``NPSD2`` o ``NCPSD``), Ip, Ii,
    Alfa, Potencia, fq, efi/b2, p lotes P, Incerteza P

donde los valores numéricos son ``ufloat`` (valor e incerteza). Los archivos
anteriores al test por lotes tienen sólo las diez primeras columnas.

La clase ``FitResults`` de ``data_fercin3_io.py`` reordena la tabla en una
fila por medición (Nivel, Medición), de modo que corrientes, potencias y
parámetros de una misma medición quedan emparejados aunque se hayan borrado
espectros o el archivo no esté ordenado por nivel. Se usan la potencia y
:math:`\alpha` de la NCPSD si hay dos detectores, o de la NPSD1 si hay uno.

**Factores de calibración.** Se ajustan rectas :math:`p = a I + b` para cada
corriente (I1, I2 e Ip) por mínimos cuadrados pesados con la incerteza de la
potencia (la incerteza de las corrientes no se usa). La pendiente :math:`a`
es el factor de calibración (:math:`f_1`, :math:`f_2`, :math:`f_p`) y la
ordenada :math:`b` debería ser compatible con cero. Se necesitan mediciones en
al menos dos niveles. También se ajustan Ip en función de I1 e I2.

**Parámetros.** :math:`\alpha` (de todas las mediciones), :math:`f_q` y
:math:`\varepsilon/\beta^2` (sólo de las mediciones con BW = 200 Hz) se
promedian con pesos :math:`w_k = 1/\sigma_k^2`:

.. math::

    \bar{x} = \frac{\sum w_k x_k}{\sum w_k}, \qquad
    u^2(\bar{x}) = \frac{s^2}{n}\,
                   \frac{\langle w^2 \rangle}{\langle w \rangle^2}

con :math:`s` el desvío estándar de los :math:`n` valores. La incerteza
proviene de la dispersión entre mediciones (con un solo valor, es su
incerteza); con pocas mediciones esa estimación tiene pocos grados de
libertad. Los valores sin incerteza (o con incerteza nula) no se usan.

**Predicciones.** Con las rectas anteriores, a partir de una potencia o de
una corriente se calculan las demás: :math:`I_j = (p - b_j)/a_j`.
