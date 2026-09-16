"""
Keep the microphone shut except while a dictation is actually recording.

Windows leaves a capture device open to every process all day long. This module
inverts that: the microphone stays closed, and a dictation opens it for the few
seconds it needs. Two independent levers are used, because they protect against
different things:

  consent - HKCU CapabilityAccessManager. The OS capability broker refuses the
            capture stream to ordinary applications. A real boundary against
            browsers, meeting apps and anything else that opens a microphone
            without asking. Writable without administrator rights, which also
            means code running as this user can flip it back.

  mute    - the endpoint mute flag on the capture device. Convenience only:
            any process undoes it with a single call. It is here because it
            takes effect instantly and shows up in the Windows volume UI, so
            the state is visible rather than silent.

Neither lever stops code that already runs as this user. The only real
guarantee remains the hardware mute button on the microphone itself.

Nothing in here may break dictation. Every failure is logged and swallowed: a
gate that cannot close is a privacy problem, but a gate that raises is a broken
application.

Both levers are Windows mechanisms with no counterpart elsewhere - the
capability broker does not exist on Linux, and the endpoint mute flag is a
WASAPI notion. On any other platform this module reports itself unsupported and
does nothing, rather than importing `winreg` and taking the whole application
down at startup. A configured gate that cannot run says so once in the log
instead of failing quietly, since believing the microphone is shut when it is
open is the one outcome worth shouting about.
"""

import atexit
import sys
from contextlib import contextmanager
from threading import Lock

from utils import ConfigManager

SUPPORTED = sys.platform == 'win32'

if SUPPORTED:
    import winreg

_CONSENT_PATH = (r'Software\Microsoft\Windows\CurrentVersion'
                 r'\CapabilityAccessManager\ConsentStore\microphone')
_ALLOW = 'Allow'
_DENY = 'Deny'

# Set once the gate has actually changed something, so the atexit hook does not
# touch a system the user never asked us to touch.
_engaged = False

# So the "this platform cannot do it" notice appears once per run rather than
# on every call to _mode(), which every open and close makes.
_warned = False


def _log(message):
    try:
        ConfigManager.console_print(f'[mic_gate] {message}')
    except Exception:
        pass


def _mode():
    """
    Return the effective gate mode: 'off', 'mute', 'consent' or 'both'.

    Always 'off' where the levers do not exist, whatever the config asks for.
    Every other function in this module branches on the answer, so one check
    here is what keeps the Windows-only calls unreachable elsewhere.
    """
    try:
        mode = ConfigManager.get_config_value('security', 'mic_gate')
    except Exception:
        return 'off'
    mode = (mode or 'off').strip().lower()

    if not SUPPORTED and mode != 'off':
        global _warned
        if not _warned:
            _warned = True
            _log(f'mic_gate is set to {mode!r}, but the gate is Windows-only. '
                 f'The microphone is NOT being closed on this platform.')
        return 'off'
    return mode


# --- consent lever -------------------------------------------------------

def _write_consent(value):
    """Set the capability-access verdict for desktop and packaged apps alike."""
    if not SUPPORTED:
        return
    for subpath in (_CONSENT_PATH, _CONSENT_PATH + r'\NonPackaged'):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, subpath, 0,
                                winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, 'Value', 0, winreg.REG_SZ, value)
        except OSError as e:
            _log(f'consent {value} failed on {subpath}: {e}')


def read_consent():
    """Return the current verdict, or None if it cannot be read."""
    if not SUPPORTED:
        return None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _CONSENT_PATH) as key:
            return winreg.QueryValueEx(key, 'Value')[0]
    except OSError:
        return None


# --- mute lever ----------------------------------------------------------

# Every COM pointer the mute lever touches is built once and held here for the
# life of the process. Nothing is ever released, and that is the whole point.
#
# A COM pointer this app drops does not die when its last name goes out of
# scope: comtypes proxies end up in reference cycles, so Release() is left to
# the cyclic garbage collector, which fires at an arbitrary later moment on
# whatever thread happens to allocate. Releasing one of pycaw's own pointers
# that way faults on this machine - reproducibly, once per call. Most of the
# time ctypes catches the access violation and prints an ignored __del__
# traceback; once it did not, and the collector fired in the middle of
# onnxruntime's DLL load during a transcription and took the process with it.
# The faulthandler stack is in ww_err.log.
#
# Holding the pointers leaves the collector nothing to release. Windows
# reclaims them when the process exits, which is when we would have released
# them anyway.
_com = {}
_com_lock = Lock()


def _endpoint():
    """
    Return the default capture endpoint's volume interface, building it once.

    CoInitialize runs on every call because COM must be initialised per thread
    and this is reached from the recording QThread as well as the GUI thread;
    it only bumps a counter once the apartment exists.
    """
    import comtypes
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.api.endpointvolume import IAudioEndpointVolume
    from pycaw.api.mmdeviceapi import IMMDeviceEnumerator
    from pycaw.constants import CLSID_MMDeviceEnumerator, EDataFlow, ERole

    try:
        comtypes.CoInitialize()
    except Exception as e:
        _log(f'CoInitialize failed: {e}')

    with _com_lock:
        if 'volume' not in _com:
            # Built by hand rather than through AudioUtilities.GetMicrophone(),
            # which drops its enumerator on return - straight into the cycle
            # collector described above. Here every intermediate is kept.
            _com['enumerator'] = comtypes.CoCreateInstance(
                CLSID_MMDeviceEnumerator, IMMDeviceEnumerator,
                comtypes.CLSCTX_INPROC_SERVER)
            _com['mic'] = _com['enumerator'].GetDefaultAudioEndpoint(
                EDataFlow.eCapture.value, ERole.eMultimedia.value)
            _com['volume'] = cast(
                _com['mic'].Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None),
                POINTER(IAudioEndpointVolume))
        return _com['volume']


def _write_mute(flag):
    try:
        _endpoint().SetMute(1 if flag else 0, None)
    except Exception as e:
        _log(f'mute {flag} failed: {e}')


def read_mute():
    """
    Return True/False, or None if the endpoint cannot be reached.

    Skipped entirely unless the mute lever is actually in use: status() calls
    this on startup, and there is no reason to drag COM into a run configured
    for the consent lever alone.
    """
    if _mode() not in ('mute', 'both'):
        return None
    try:
        return bool(_endpoint().GetMute())
    except Exception:
        return None


# --- gate ----------------------------------------------------------------

def close():
    """Shut the microphone. Safe to call repeatedly and when already shut."""
    global _engaged
    mode = _mode()
    if mode == 'off':
        return
    if mode in ('consent', 'both'):
        _write_consent(_DENY)
    if mode in ('mute', 'both'):
        _write_mute(True)
    _engaged = True


def open_():
    """Open the microphone for a recording. Named with a trailing underscore
    so it does not shadow the builtin at call sites."""
    mode = _mode()
    if mode == 'off':
        return
    # Consent is lifted first: the capability broker decides when the capture
    # stream is created, so a late Allow would arrive after sounddevice has
    # already been refused.
    if mode in ('consent', 'both'):
        _write_consent(_ALLOW)
    if mode in ('mute', 'both'):
        _write_mute(False)


@contextmanager
def recording_session():
    """Open the microphone for the duration of a recording, then shut it."""
    open_()
    try:
        yield
    finally:
        close()


def status():
    """Human-readable state, for the settings UI and the audit script."""
    return {'mode': _mode(), 'consent': read_consent(), 'muted': read_mute(),
            'supported': SUPPORTED}


@atexit.register
def _shut_on_exit():
    """
    Leave the microphone closed when the app goes away.

    Closed is the fail-safe direction: a crash that leaves the gate shut costs
    the user one toggle, while a crash that leaves it open silently restores
    the always-listening state this module exists to remove.
    """
    if _engaged:
        close()
