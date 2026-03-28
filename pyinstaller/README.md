# Generación de ejecutables

Los ejecutables se generan con PyInstaller y producen una carpeta
auto-contenida que corre sin necesidad de tener Python instalado.

## Requisitos

```bash
pip install pyinstaller
```

También es necesario haber generado la documentación HTML antes de empaquetar:

```bash
make docs
make dist   # esto copia docs/_build/html → src/ruidaqan/docs/html
```

## Generar todos los ejecutables

```bash
# Desde la raíz del repo, con el venv activo:
make -f Makefile.exe exe
```

O individualmente:

```bash
make -f Makefile.exe exe_procesamiento
make -f Makefile.exe exe_resultados
make -f Makefile.exe exe_adquisicion
```

## Resultado

Se generan tres carpetas en `dist/`:

```
dist/
├── ruidaqan-adquisicion/
│   └── ruidaqan-adquisicion      ← ejecutable (Linux) o .exe (Windows)
├── ruidaqan-procesamiento/
│   └── ruidaqan-procesamiento
└── ruidaqan-resultados/
    └── ruidaqan-resultados
```

Para distribuir, comprimí cada carpeta en un zip:

```bash
cd dist
zip -r ruidaqan-procesamiento-linux.zip ruidaqan-procesamiento/
zip -r ruidaqan-resultados-linux.zip    ruidaqan-resultados/
zip -r ruidaqan-adquisicion-linux.zip   ruidaqan-adquisicion/
```

## Comportamiento por sistema operativo

| Ventana        | Linux                        | Windows                  |
|---------------|------------------------------|--------------------------|
| Adquisición   | Fuerza `DEBUG_MODE=True`     | Usa drivers NI reales    |
| Procesamiento | `DEBUG_MODE=True` (no afecta)| Normal                   |
| Resultados    | `DEBUG_MODE=True` (no afecta)| Normal                   |

## Solución de problemas comunes

**La ventana de ayuda no aparece:**
Asegurate de haber corrido `make docs` y `make dist` antes de empaquetar.
Los archivos HTML deben estar en `src/ruidaqan/docs/html/`.

**Error con `tables` o `numexpr`:**
Son módulos con extensiones C que PyInstaller a veces no detecta.
Ya están en `hiddenimports` en los `.spec`, pero si sigue fallando:
```bash
pip install pyinstaller-hooks-contrib
```

**Error con PyQt6 WebEngine en Linux:**
Puede requerir instalar `libxcb` y dependencias del sistema:
```bash
sudo apt install libxcb-xinerama0 libxcb-icccm4 libxcb-image0 \
                 libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 \
                 libxcb-xkb1 libxkbcommon-x11-0
```
