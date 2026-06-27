block_cipher = None

a = Analysis(
    ["app/__main__.py"],
    pathex=["."],
    binaries=[],
    datas=[],
    hiddenimports=[
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
        "httpx",
    ],
    hookspath=[],
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name="loginlogbook-client",
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon=None,
)
