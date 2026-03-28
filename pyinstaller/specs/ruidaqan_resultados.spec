# ruidaqan_resultados.spec
# Uso (desde la raíz del repo):
#   pyinstaller pyinstaller/specs/ruidaqan_resultados.spec --noconfirm

from pathlib import Path

REPO  = Path(SPECPATH).parent.parent
ENTRY = Path(SPECPATH).parent / "entrypoints"
SRC   = REPO / "src" / "ruidaqan"

block_cipher = None

a = Analysis(
    [str(ENTRY / "ruidaqan_resultados.py")],
    pathex=[str(REPO / "src")],
    binaries=[],
    datas=[
        (str(SRC / "transferencias"), "ruidaqan/transferencias"),
        (str(SRC / "constants"),      "ruidaqan/constants"),
        (str(SRC / "docs" / "html"),  "ruidaqan/docs/html"),
    ],
    hiddenimports=[
        "ruidaqan.constants.constantes_reactores",
        "PyQt6.QtWebEngineWidgets",
        "PyQt6.QtWebEngineCore",
        "PyQt6.QtPrintSupport",
        "tables",
        "numexpr",
        "lmfit",
        "uncertainties",
        "seaborn",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["nidaqmx"],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ruidaqan-resultados",
    debug=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ruidaqan-resultados",
)
