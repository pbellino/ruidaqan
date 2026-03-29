# RuiDAQAn

![GitHub release](https://img.shields.io/github/v/release/pbellino/ruidaqan)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/github/license/pbellino/ruidaqan)

**Adquisición y análisis de señales para la técnica de ruido neutrónico**

---

## Descripción

**ruidaqan** es un paquete Python para la adquisición, procesamiento espectral y análisis de resultados de señales de ruido neutrónico, orientado a la calibración en potencia de reactores nucleares.

Cuenta con tres interfaces gráficas independientes que pueden usarse por separado o en conjunto, y también puede importarse como módulo para procesamiento por scripts.

---

## Interfaces gráficas

### Adquisición (`ruidaqan a`)

Adquiere señales analógicas en tiempo real usando el API [nidaqmx](https://github.com/ni/nidaqmx-python) de National Instruments. Compatible con la mayoría de las tarjetas DAQ de NI.

Por cada cadena de medición se adquieren tres señales:
- Componente AC luego del filtro anti-aliasing
- Componente DC
- Componente AC a la entrada del filtro anti-aliasing

Está diseñada para trabajar con los equipos CNEA-K330 (amplificador) y CNEA-K231 (filtro anti-aliasing), aunque admite parámetros para otros equipos.

**Características principales:**
- Número de cadenas de medición configurable
- Selección libre de tarjeta NI disponible
- Ajuste de rango automático
- Monitoreo de saturación con interrupción automática de la adquisición
- Señales adquiridas en int16 y convertidas a voltaje con coeficientes de calibración
- Grabación en formato compatible con FERCIN-3 y en HDF5

**Control de saturación:**

| Situación | AC (5V) | AC entrada filtro (4V) | DC |
|-----------|---------|------------------------|----|
| Ajuste de rango — fondo | No detiene | No detiene | — |
| Medición de fondo | No detiene | No detiene | Sí detiene |
| Ajuste de rango — medición | Sí detiene | Sí detiene | Sí detiene |
| Medición | Sí detiene | Sí detiene | Sí detiene |

### Procesamiento (`ruidaqan p`)

Lee archivos `.RUI` (grabados por FERCIN-3) y archivos `.h5` generados por la adquisición. Realiza ajustes de espectros y estima parámetros cinéticos del reactor.

### Resultados (`ruidaqan r`)

Lee los resultados del procesamiento y calcula factores de calibración en potencia, promedios de parámetros cinéticos y ajustes lineales.

---

## Instalación

Se recomienda usar Python 3.10 dentro de un entorno virtual. Es necesario tener instaladas las [bibliotecas HDF5](https://www.hdfgroup.org).

**Desde el código fuente:**
```bash
git clone https://github.com/pbellino/ruidaqan
cd ruidaqan
python -m pip install .
```

Para desarrollo (sin reinstalar al modificar el código):
```bash
python -m pip install -e ".[dev]"
```

**Desde PyPI:**
```bash
pip install ruidaqan
```

**Desde el ejecutable** (sin necesidad de Python):

Descargar el zip correspondiente al sistema operativo desde la sección [Releases](https://github.com/pbellino/ruidaqan/releases), descomprimir y ejecutar directamente.

---

## Uso

### Interfaces gráficas

```bash
ruidaqan a   # adquisición
ruidaqan p   # procesamiento
ruidaqan r   # resultados
```

Al abrir por primera vez se pedirá seleccionar una carpeta de trabajo donde se guardarán los datos. Esta elección se recuerda en sesiones posteriores y puede cambiarse desde el menú.

### Simulación de adquisición (sin hardware NI)

En Linux o macOS:
```bash
export RUIDAQAN_DEBUG_MODE=True
ruidaqan a
```

En Windows (cmd):
```
set RUIDAQAN_DEBUG_MODE=True
```

En Windows (PowerShell):
```
$env:RUIDAQAN_DEBUG_MODE="True"
```

Con esta opción activa, las señales adquiridas son realizaciones aleatorias de procesos Gaussianos. Las interfaces de procesamiento y resultados no requieren esta variable.

### Como módulo Python

Procesar archivos `.h5`:
```python
from ruidaqan.script import HDF5FileProcessing
from ruidaqan.constants import RA3 as REACTOR

rui = HDF5FileProcessing("S001-N2-1.h5")
espectros, fs = rui.get_spectrums(512, 0)
norm_espectros, fs = rui.get_normalized_spectrums("RA3", freqs_to_remove=[50, 100, 150])

if rui.BW == 200:
    intervalos = 2 * [(2.3, 178.9)] + [(2.3, 93)]
elif rui.BW == 40:
    intervalos = 3 * [(2.8, 35.8)]

rui.fit_spectrums(intervalos, plot=True)
rui.calcula_parametros_cineticos(REACTOR)
```

Analizar resultados de una calibración:
```python
from ruidaqan.script import FitResults

fit_results = FitResults("S001-resultados_ajustes.pkl")
fit_results.fit_p_vs_I()
fit_results.fit_Ip_vs_I(plot=True)
fit_results.average_parameters(plot=True)
```

---

## Funciones de transferencia

Las funciones de transferencia de los reactores se encuentran en `src/ruidaqan/transferencias/`, organizadas por reactor. Si necesitás agregar o modificar funciones de transferencia, copiá o editá los archivos `.PSD` en la carpeta correspondiente al reactor.

---

## Plataformas

| Sistema | Adquisición | Procesamiento | Resultados |
|---------|-------------|---------------|------------|
| Windows | ✓ (con drivers NI) | ✓ | ✓ |
| Linux   | ✓ (modo simulación) | ✓ | ✓ |

Los drivers de NI (`nidaqmx`) solo están disponibles para Windows. En Linux se puede usar el modo de simulación para desarrollo y pruebas, y las interfaces de procesamiento y resultados funcionan sin restricciones.

---

## Documentación

La documentación completa está disponible en la carpeta `docs/` y puede generarse con:

```bash
make docs
```

---

## Licencia

Ver archivo [LICENSE](LICENSE).

---

## Contribuidores

- Pablo Bellino (pablobellino@cnea.gob.ar) — Reactor RA-3, CNEA
