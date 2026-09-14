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
"""

import atexit
import winreg
from contextlib import contextmanager

from utils import ConfigManager

_CONSENT_PATH = (r'Software\Microsoft\Windows\CurrentVersion'
                 r'\CapabilityAccessManager\ConsentStore\microphone')
_ALLOW = 'Allow'
_DENY = 'Deny'

# Set once the gate has actually changed something, so the atexit hook does not
# touch a system the user never asked us to touch.
_engaged = False


def _log(message):
    try:
        ConfigManager.console_print(f'[mic_gate] {message}')
    except Exception:
        pass


def _mode():
    """Return the configured gate mode: 'off', 'mute', 'consent' or 'both'."""
    try:
        mode = ConfigManager.get_config_value('security', 'mic_gate')
    except Exception:
        return 'off'
    return (mode or 'off').strip().lower()


# --- consent lever -------------------------------------------------------

def _write_consent(value):
    """Set the capability-access verdict for desktop and packaged apps alike."""
    for subpath in (_CONSENT_PATH, _CONSENT_PATH + r'\NonPackaged'):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, subpath, 0,
                                winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, 'Value', 0, winreg.REG_SZ, value)
        except OSError as e:
            _log(f'consent {value} failed on {subpath}: {e}')


def read_consent():
    """Return the current verdict, or None if the key cannot be read."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _CONSENT_PATH) as key:
            return winreg.QueryValueEx(key, 'Value')[0]
    except OSError:
        return None


# --- mute lever ----------------------------------------------------------

def _endpoint():
    """
    Return the default capture endpoint's volume interface.

    COM is initialised explicitly: this runs inside a QThread, where nothing
    else has done it, and pycaw would otherwise fail on the first call.
    """
    import comtypes
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

    try:
        comtypes.CoInitialize()
    except Exception:
        pass
    mic = AudioUtilities.GetMicrophone()
    return cast(mic.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None),
                POINTER(IAudioEndpointVolume))


def _write_mute(flag):
    try:
        _endpoint().SetMute(1 if flag else 0, None)
    except Exception as e:
        _log(f'mute {flag} failed: {e}')


def read_mute():
    """Return True/False, or None if the endpoint cannot be reached."""
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
    return {'mode': _mode(), 'consent': read_consent(), 'muted': read_mute()}


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
