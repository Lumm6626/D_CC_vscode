# -*- mode: python ; coding: utf-8 -*-
import os

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['Pillow', 'PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.QtSvg',
              'PySide6.QtPrintSupport', 'PySide6.QtSql', 'PySide6.QtTest',
              'PySide6.QtOpenGL', 'PySide6.QtOpenGLWidgets',
              'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets',
              'PySide6.QtXml', 'PySide6.QtHelp', 'PySide6.QtMultimedia',
              'PySide6.QtMultimediaWidgets', 'PySide6.QtBluetooth',
              'PySide6.QtNfc', 'PySide6.QtSensors', 'PySide6.QtSerialPort',
              'PySide6.QtTextToSpeech', 'PySide6.QtWebSockets',
              'unittest', 'test', 'email', 'http', 'xmlrpc', 'pip'],
    noarchive=False,
    optimize=2,
)

# 排除不需要的大文件
SKIP_BINARIES = {
    'opengl32sw.dll', 'd3dcompiler_47.dll',
    'libegl.dll', 'libglesv2.dll',
    'qt6pdf.dll',
    'qt6qml.dll', 'qt6quick.dll', 'qt6quickwidgets.dll',
    'qt6opengl.dll', 'qt6openglwidgets.dll',
}

filtered_binaries = []
for name, path, typ in a.binaries:
    base = os.path.basename(name).lower()
    if base in SKIP_BINARIES:
        continue
    filtered_binaries.append((name, path, typ))

# 排除翻译文件
filtered_datas = []
for name, path, typ in a.datas:
    if 'translations' in name.lower() and not name.endswith('qt_zh-CN.qm'):
        continue
    filtered_datas.append((name, path, typ))

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    filtered_binaries,
    filtered_datas,
    name='ScreenshotTool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['app.ico'],
)
