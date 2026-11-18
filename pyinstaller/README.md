# Generación de ejecutables

Los ejecutables se generan con PyInstaller y producen una carpeta
auto-contenida que corre sin necesidad de tener Python instalado.

## Requisitos

```bash
pip install pyinstaller
```

## Generar todos los ejecutables

Desde la raíz del repo, con el entorno activo (funciona igual en Windows y en
Linux):

```bash
make exe
# o, sin make:
python scripts/empaqueta.py exe
```

O individualmente:

```bash
make exe_procesamiento
python scripts/empaqueta.py exe procesamiento resultados
```

El script compila la documentación y la copia a `src/ruidaqan/docs/html`
(para que la ayuda quede dentro del ejecutable), estampa el hash del commit en
`src/ruidaqan/__init__.py` mientras se empaqueta y después lo deja como
estaba.

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
Generá los ejecutables con `make exe` (o `python scripts/empaqueta.py exe`),
que compila la ayuda y la copia a `src/ruidaqan/docs/html/` antes de
empaquetar.

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
