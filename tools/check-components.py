"""
Do the native components load? Run by tools\install.ps1 right after the
requirements are installed, with the venv's python.

The same two steps as the top of src\main.py: name venv\Scripts as a DLL
directory (the Visual C++ runtime from requirements.txt lives there, and the
venv's python.exe is only a launcher, so Windows would not look there on its
own), then import the two packages with native code that needs it. Prints
`ok` and exits 0, or lets the ImportError through with exit code 1 - the
installer shows it and stops, which beats an app that silently never starts.

A file rather than `python -c`: Windows PowerShell 5.1 strips the quotes out
of a -c string on the way to the native command, and the check failed on its
own syntax instead of testing anything.
"""
import os
import sys

if sys.platform == 'win32' and hasattr(os, 'add_dll_directory'):
    os.add_dll_directory(os.path.dirname(os.path.abspath(sys.executable)))

import ctranslate2  # noqa: E402,F401
import onnxruntime  # noqa: E402,F401

print('ok')
