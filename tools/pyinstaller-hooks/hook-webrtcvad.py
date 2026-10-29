"""
Override for PyInstaller's bundled webrtcvad hook.

The bundled hook copies the metadata of a distribution called `webrtcvad`.
This project installs `webrtcvad-wheels` - the same `webrtcvad` module, from
a fork that ships prebuilt wheels - and there is no distribution by the
original name, so the bundled hook stops the build with
PackageNotFoundError. Hooks in the spec's `hookspath` win over the bundled
ones; this one copies the metadata that does exist and nothing else.
"""
from PyInstaller.utils.hooks import copy_metadata

datas = copy_metadata('webrtcvad-wheels')
