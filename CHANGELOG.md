# Cambios

## Sin publicar

### Cambia los resultados

- **Estimación espectral y ajuste por defecto**: ventana rectangular (antes
  Hann) y ajuste por mínimos cuadrados pesados con la varianza del estimador
  de Welch (antes sin pesos). Ambas opciones se pueden cambiar en la ventana
  de procesamiento.
- **Incertezas**: con el método anterior la incerteza de la potencia y de
  alfa de cada medición estaba subestimada en un factor ~2-3 (simulación con
  los parámetros por defecto: 1.5 % informado contra 5.3 % real para la
  potencia). Con el método nuevo es correcta en mediciones estacionarias, por
  lo que **las incertezas son mayores que las de las series procesadas con
  versiones anteriores**. Los valores de potencia y alfa cambian sólo dentro
  del ruido estadístico (diferencia media entre ventanas +0.6 % ± 0.4 % en 29
  mediciones de tres series). Los promedios de varias mediciones de un mismo
  nivel no cambian de forma sistemática, porque ya usaban la dispersión entre
  mediciones.
- **Test por lotes de la potencia**: después de cada ajuste se compara la
  incerteza del ajuste con la de lotes de historias mediante un test chi^2
  (nivel 0.01). Si se rechaza (medición no estacionaria o modelo
  insuficiente), se informa la incerteza por lotes y la medición se marca.
- **.RUI en carpetas con guion o con ruta relativa**: se buscaba mal el
  archivo de coeficientes de conversión y se usaban los genéricos de la
  NI USB-6353. Las series afectadas pueden cambiar de escala al reprocesarse.

### Archivos

- `SXXX-resultados_ajustes.pkl` tiene dos columnas nuevas (valor p del test
  e incerteza usada). Los archivos anteriores se leen igual (columnas
  vacías); al grabar pasan al formato nuevo, que las versiones anteriores no
  pueden leer.
- Los .RUI y .PSD de los programas de DOS con acentos en los comentarios
  (codificación cp850) ahora se pueden leer.

### Correcciones

- Adquisición: se emite una copia del buffer (antes una lectura podía
  sobrescribir una historia antes de que el GUI la copiara) y se avisa si la
  placa da un error.
- `ajuste_apsd`/`ajuste_cpsd` con incertezas ('daata'), covarianza de
  `ajuste_lineal` sin incertezas, transferencia de distinto largo que el
  espectro, `__commit__` desde otro repositorio.
- La curva de ajuste del gráfico se calcula con el modelo (con el ajuste
  pesado el residuo está dividido por la incerteza).
- **Núcleo**: las constantes del núcleo indicado en el .h5 no se aplicaban
  nunca: RA-6 N016 y RP-10 N008 se procesaban con las constantes de N011
  y N007. La potencia quedaba +4.7 % alta en RA-6 N016 y −5.1 % baja en
  RP-10 N008. Las series de esos núcleos se deben reprocesar.
- **Resultados**: corrientes, potencias y parámetros se emparejaban por su
  posición en el archivo. Al borrar una fila de una sola medición los
  ajustes p vs I mezclaban mediciones o la serie dejaba de poder abrirse, y
  si el archivo no estaba ordenado por nivel los gráficos de fq vs I
  quedaban desapareados. Ahora se emparejan por (Nivel, Medición).
- Resultados: los borrados se graban al cerrar la ventana (o al abrir otro
  archivo), después de pedir confirmación. Antes se grababan enseguida.
- Resultados: las predicciones usan la ordenada del ajuste
  (p = a I + b) y ya no se disparan en cadena entre las casillas.
- Resultados: con un solo nivel, o al abrir otro archivo, quedaban los
  ajustes y el resumen anteriores. Ya no se cierra la ventana al dejar un
  ajuste sin puntos o con uno solo, ni se pierde la casilla de I2 al abrir
  un archivo de un detector y después uno de dos.
- "Grabar" con la ventana de resultados de otra serie abierta agregaba los
  datos al archivo de esa otra serie.
- `FitResults.fit_Ip_vs_I` reemplazaba el método por su resultado: una
  segunda llamada fallaba. El resultado ahora está en `fited_Ip_vs_I`.
- Incerteza de la Ip ingresada a mano con un solo valor: se grababa
  sigma^2 en lugar de sigma.
- Procesamiento y resultados abiertos solos (`ruidaqan p`, `ruidaqan r`)
  arrancaban siempre en la carpeta de trabajo, aunque se hubiera abierto un
  archivo de otra carpeta. Ahora recuerdan la última carpeta desde la que se
  abrió un archivo (`carpeta_lectura` en `config.json`); la carpeta de
  trabajo de la adquisición sólo cambia desde el menú de la ventana
  principal. Cancelar el diálogo de abrir ya no deja la carpeta vacía.

### Correcciones de la revisión (segunda parte)

- **Saturación**: sólo se detectaba en el extremo positivo del rango de la
  placa (+32767) y del filtro antialias (+4 V). Ahora también en el
  negativo. El indicador de utilización del rango usa el valor absoluto.
- Control de las DC durante la adquisición: con señales negativas los
  límites del 1 % quedaban invertidos (colores rojo/azul al revés).
- Procesamiento: un archivo que no se puede abrir, uno con nombre fuera del
  formato SXXX-NY-Z, un reactor sin constantes o sin funciones transferencia
  ya no cierran el programa ni se procesan en silencio con las constantes
  del archivo anterior: se avisa. Sin nombre válido no se habilita "Grabar".
- Resultados: un `.pkl` dañado se avisa al abrirlo y "Grabar" no lo
  sobrescribe.
- CIp manual: se rechazan valores no numéricos e incertezas nulas o
  negativas (daban NaN en la Ip). Acepta coma decimal. El archivo de
  recuperación se guarda junto a la medición
  (`SXXX-NY-Z-ingresos_manuales_cip.pkl`) y no en el directorio desde el
  que se ejecuta el programa.
- El nombre del .RUI se armaba reemplazando "S0" en toda la ruta.
- Colores de la tabla de resultados según el tema del sistema (siempre se
  usaban los del tema oscuro); valores faltantes vacíos en lugar de
  "nan+/-nan".
- `modifica_corrientes_fondo.py` modificaba archivos del directorio actual
  al importarse.
- Bloques `__main__` con PyQt5, `\d` sin raw string, dirección de correo
  del "Acerca de".

### Para desarrolladores

- `HDF5FileProcessing` y `RUIFileProcessing` comparten la clase base
  `_ProcesamientoEspectral`.
- Nuevos métodos: `incerteza_por_lotes`, `aplica_test_lotes`,
  `segmentos_equivalentes`; parámetros `window` y `ponderado`.
- Tests con mediciones sintéticas que corren en el CI (`tests/sintetico.py`).
