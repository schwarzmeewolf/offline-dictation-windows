"""
Make a pip-installed CUDA runtime findable on Windows.

CTranslate2 does not link cuBLAS and cuDNN at load time - it asks Windows for
them by name the first time a model actually runs on the GPU. When those
libraries come from the `nvidia-cublas-cu12` and `nvidia-cudnn-cu12` wheels
they sit inside site-packages, where nothing looks for them, so the model
loads happily and then dies at the first encode with

    RuntimeError: Library cublas64_12.dll is not found or cannot be loaded

`os.add_dll_directory` does not fix this: it only affects loads that opt into
the newer search flags, and CTranslate2's does not. Prepending the directories
to PATH does, because that is one of the places a plain LoadLibrary looks.

Harmless when there is no GPU and no wheels: the directories simply do not
exist and nothing is added - and equally harmless off Windows, where the glob
matches nothing because the wheels lay their libraries out differently.

That harmlessness is not a Linux implementation, though. The same problem
exists there and needs a different answer: the dynamic loader reads
LD_LIBRARY_PATH once when the process starts, so setting it from inside a
running Python is already too late, and the libraries have to be pulled in
directly with ctypes.CDLL instead. Until that is written, a GPU on Linux falls
back to the CPU at startup like any other unusable device.
"""

import glob
import os
import sysconfig


def enable():
    """
    Put the pip-installed CUDA library directories on PATH.

    Must run before the first GPU model is created. Importing this module
    costs nothing but the standard library, so it is safe to call it ahead of
    ctranslate2 without disturbing the import order that module needs.

    :return: the directories that were added, in search order
    """
    site_packages = sysconfig.get_paths().get('purelib')
    if not site_packages:
        return []

    pattern = os.path.join(site_packages, 'nvidia', '*', 'bin')
    directories = [os.path.abspath(d) for d in sorted(glob.glob(pattern))
                   if os.path.isdir(d)]
    if not directories:
        return []

    current = os.environ.get('PATH', '')
    already = set(current.split(os.pathsep))
    missing = [d for d in directories if d not in already]
    if missing:
        os.environ['PATH'] = os.pathsep.join(missing + [current])
    return directories
