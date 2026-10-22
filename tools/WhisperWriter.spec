# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller recipe for the Windows build. Run through tools\build-exe.ps1.

One folder, not one file: a single-file build unpacks half a gigabyte of
Qt and CTranslate2 into %TEMP% at every start, and the app finds its
settings, assets and logs by paths relative to where it runs - which a
temp folder is not. The folder keeps `WhisperWriter.exe` beside `_internal`,
and the build script copies `assets` and the documents next to the exe.

CPU only, on purpose. The GPU libraries are 2 GB on their own and would
push the archive past what a release can carry; `cuda_libs` finds nothing
and the app says `Falling back to CPU`, which is the truth.

What is collected whole, and why:
- ctranslate2: native DLLs the hooks do not all find.
- faster_whisper: ships the Silero VAD model as a data file.
- av: FFmpeg DLLs, loaded at import.
- comtypes, pycaw: COM glue for the microphone mute lever; comtypes
  generates wrapper modules at import time and wants its whole tree.

onnxruntime (faster-whisper's VAD, on by default in this fork) is NOT
collected whole: `collect_all` imports every submodule to find their DLLs,
and importing `onnxruntime.quantization` in that probe process dies with an
access violation (exit 0xC0000005), which took three builds to see. The app
only needs the core - `onnxruntime.capi` with its three DLLs - so that is
what is taken, and the tool/training subpackages are excluded outright.
"""
import os

from PyInstaller.utils.hooks import (collect_all, collect_data_files,
                                     collect_dynamic_libs)

ROOT = os.path.abspath(os.path.join(SPECPATH, '..'))

# utils.py reads config_schema.yaml from the folder its own file is in,
# which inside the bundle is _internal - so the schema goes to the top of it.
datas = [(os.path.join(ROOT, 'src', 'config_schema.yaml'), '.')]
binaries = []
hiddenimports = []

for package in ('ctranslate2', 'faster_whisper', 'av', 'comtypes', 'pycaw'):
    d, b, h = collect_all(package)
    datas += d
    binaries += b
    hiddenimports += h

binaries += collect_dynamic_libs('onnxruntime')
datas += collect_data_files('onnxruntime', includes=['capi/*.json', 'capi/*.txt'])
hiddenimports += ['onnxruntime.capi', 'onnxruntime.capi._pybind_state',
                  'onnxruntime.capi.onnxruntime_pybind11_state']

a = Analysis(
    [os.path.join(ROOT, 'src', 'main.py')],
    pathex=[os.path.join(ROOT, 'src')],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    # Our hooks win over PyInstaller's bundled ones. See the folder for why.
    hookspath=[os.path.join(ROOT, 'tools', 'pyinstaller-hooks')],
    excludes=['torch', 'tkinter', 'matplotlib', 'IPython', 'jupyter',
              'PyQt5.QtWebEngine', 'PyQt5.QtWebEngineWidgets',
              'onnxruntime.quantization', 'onnxruntime.transformers',
              'onnxruntime.tools', 'onnxruntime.datasets',
              'onnxruntime.backend'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='WhisperWriter',
    console=False,                 # no console, like pythonw: logs go to files
    icon=os.path.join(ROOT, 'assets', 'ww-logo.ico'),
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='WhisperWriter',
)
