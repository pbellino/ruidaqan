# ruidaqan_adquisicion.spec
# Uso (desde la raíz del repo):
#   pyinstaller pyinstaller/specs/ruidaqan_adquisicion.spec --noconfirm

from pathlib import Path

# SPECPATH = pyinstaller/specs/
REPO  = Path(SPECPATH).parent.parent          # raíz del repo
ENTRY = Path(SPECPATH).parent / "entrypoints" # pyinstaller/entrypoints/
SRC   = REPO / "src" / "ruidaqan"

block_cipher = None

a = Analysis(
    [str(ENTRY / "ruidaqan_adquisicion.py")],
    pathex=[str(REPO / "src")],
    binaries=[],
    datas=[
        (str(SRC / "transferencias"), "ruidaqan/transferencias"),
        (str(SRC / "constants"),      "ruidaqan/constants"),
        (str(SRC / "docs" / "html"),  "ruidaqan/docs/html"),
        (str(SRC / "gui" / "config.py"), "ruidaqan/gui"), 
    ],
    hiddenimports=[
        "ruidaqan.constants.constantes_reactores",
        "PyQt6.QtWebEngineWidgets",
        "PyQt6.QtWebEngineCore",
        "PyQt6.QtPrintSupport",
        "nidaqmx",
        "tables",
        "numexpr",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ruidaqan-adquisicion",
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
    name="ruidaqan-adquisicion",
)
