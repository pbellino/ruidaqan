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

### Para desarrolladores

- `HDF5FileProcessing` y `RUIFileProcessing` comparten la clase base
  `_ProcesamientoEspectral`.
- Nuevos métodos: `incerteza_por_lotes`, `aplica_test_lotes`,
  `segmentos_equivalentes`; parámetros `window` y `ponderado`.
- Tests con mediciones sintéticas que corren en el CI (`tests/sintetico.py`).
