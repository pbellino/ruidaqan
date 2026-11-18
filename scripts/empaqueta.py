#!/usr/bin/env python3
"""
Arma el paquete instalable y los ejecutables, en Windows y en Linux.

    python scripts/empaqueta.py dist
        Compila la documentación, la copia a src/ruidaqan/docs/html, estampa
        el hash del commit en src/ruidaqan/__init__.py y arma el paquete
        (python -m build). Al terminar, __init__.py queda como estaba.

    python scripts/empaqueta.py exe [adquisicion procesamiento resultados]
        Lo mismo que dist y además genera los ejecutables con PyInstaller
        (por defecto los tres).

    python scripts/empaqueta.py limpia
        Borra dist/, build/ y src/*.egg-info.

Con --sin-aislamiento (dist y exe) el paquete se arma con el setuptools y el
wheel del entorno actual (python -m build --no-isolation), sin crear un
entorno aislado ni descargar nada de PyPI. Sirve detrás de un proxy o sin
conexión.

Reemplaza a las recetas del Makefile, que usaban herramientas de Unix
(mkdir -p, cp, sed, git restore) y no funcionaban con el make de Windows.
Se usa el mismo intérprete de Python con el que se ejecuta este script.
"""

import argparse
import re
import shutil
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
INIT = RAIZ / "src" / "ruidaqan" / "__init__.py"
DOCS_BUILD = RAIZ / "docs" / "_build" / "html"
DOCS_PAQUETE = RAIZ / "src" / "ruidaqan" / "docs" / "html"
SPECS = RAIZ / "pyinstaller" / "specs"
EJECUTABLES = ("adquisicion", "procesamiento", "resultados")


def corre(*args):
    """ Ejecuta un comando desde la raíz del repositorio; corta si falla """
    print("$", " ".join(str(a) for a in args), flush=True)
    subprocess.run([str(a) for a in args], cwd=RAIZ, check=True)


def compila_documentacion():
    corre(sys.executable, "-m", "sphinx", "-b", "html", "docs", DOCS_BUILD)
    # Se reemplaza la copia anterior completa para que no queden páginas o
    # imágenes viejas
    if DOCS_PAQUETE.exists():
        shutil.rmtree(DOCS_PAQUETE)
    shutil.copytree(DOCS_BUILD, DOCS_PAQUETE)
    print(f"Documentación copiada a {DOCS_PAQUETE.relative_to(RAIZ)}")


def hash_commit():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=RAIZ,
            text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "desconocido"


@contextmanager
def hash_estampado():
    """
    Estampa el hash del commit en __init__.py mientras dura el bloque y
    después deja el archivo exactamente como estaba (también si hay errores).
    """
    original = INIT.read_bytes()
    texto = original.decode("utf-8")
    h = hash_commit()
    nuevo, n = re.subn(r'^__commit__ =.*$', f'__commit__ = "{h}"', texto,
                       count=1, flags=re.MULTILINE)
    if n != 1:
        raise RuntimeError(f"No se encontró '__commit__ =' en {INIT}")
    INIT.write_bytes(nuevo.encode("utf-8"))
    print(f"Hash {h} estampado en {INIT.relative_to(RAIZ)}")
    try:
        yield h
    finally:
        INIT.write_bytes(original)
        print(f"{INIT.relative_to(RAIZ)} restaurado")


def arma_paquete(sin_aislamiento=False):
    extra = ["--no-isolation"] if sin_aislamiento else []
    corre(sys.executable, "-m", "build", *extra)


def dist(sin_aislamiento=False):
    compila_documentacion()
    with hash_estampado():
        arma_paquete(sin_aislamiento)


def exe(nombres, sin_aislamiento=False):
    compila_documentacion()
    with hash_estampado():
        arma_paquete(sin_aislamiento)
        for nombre in nombres:
            corre(sys.executable, "-m", "PyInstaller",
                  SPECS / f"ruidaqan_{nombre}.spec", "--noconfirm")
    print("Ejecutables generados en dist/")


def limpia():
    for c in [RAIZ / "dist", RAIZ / "build",
              *(RAIZ / "src").glob("*.egg-info")]:
        if c.exists():
            shutil.rmtree(c)
            print(f"Borrado {c.relative_to(RAIZ)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="comando", required=True)
    p_dist = sub.add_parser("dist",
                            help="paquete instalable con la documentación")
    p_exe = sub.add_parser("exe", help="paquete y ejecutables (PyInstaller)")
    for p in (p_dist, p_exe):
        p.add_argument("--sin-aislamiento", action="store_true",
                       help="usa setuptools y wheel del entorno actual (no "
                            "descarga nada; útil detrás de un proxy)")
    # Sin default en argparse (algunas versiones validan el default de
    # nargs="*" contra choices): vacío = los tres
    p_exe.add_argument("nombres", nargs="*", choices=EJECUTABLES,
                       metavar="ejecutable",
                       help=f"cuáles generar: {', '.join(EJECUTABLES)}")
    sub.add_parser("limpia", help="borra dist/, build/ y src/*.egg-info")
    args = parser.parse_args()
    try:
        if args.comando == "dist":
            dist(args.sin_aislamiento)
        elif args.comando == "exe":
            exe(args.nombres or list(EJECUTABLES), args.sin_aislamiento)
        else:
            limpia()
    except subprocess.CalledProcessError as e:
        sys.exit(f"Falló: {' '.join(map(str, e.cmd))}")


if __name__ == "__main__":
    main()
