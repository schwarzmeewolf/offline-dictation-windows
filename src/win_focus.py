"""
Remember which window dictation started in, and hand the focus back to it.

Text is typed into whatever window has the focus at the moment of typing, which
is not necessarily the window the user was dictating into. Between pressing the
activation key and the text arriving there are seconds of recording and
transcription, and anything can come to the front in that time: a notification,
another application finishing its start-up, the user glancing at something
else. When the status window used to take the focus, Windows gave it back on
closing to whichever window was top of the stack - not to the one it was taken
from - and the dictation landed in a different program altogether.

The status window no longer takes the focus at all; this module covers the rest.
The foreground window is noted when recording starts, and before typing, if the
focus has moved on, it is handed back.

Windows guards the foreground: a process that is not in front may not simply
bring another window there, or every background program could steal the user's
typing. The documented way through is to attach our input queue to that of the
thread currently in front for the duration of the call; with the queues shared,
the request counts as coming from the foreground. Even so Windows may refuse,
and restore() says whether it worked rather than assuming so.

Guarded like win_input: on any other platform the functions do nothing.
"""
import sys


def available():
    """Whether this module can be used on the running platform."""
    return sys.platform == 'win32'


if available():
    import ctypes
    from ctypes import wintypes

    _user32 = ctypes.WinDLL('user32', use_last_error=True)
    _kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

    _user32.GetForegroundWindow.restype = wintypes.HWND
    _user32.SetForegroundWindow.argtypes = (wintypes.HWND,)
    _user32.SetForegroundWindow.restype = wintypes.BOOL
    _user32.IsWindow.argtypes = (wintypes.HWND,)
    _user32.IsWindow.restype = wintypes.BOOL
    _user32.IsIconic.argtypes = (wintypes.HWND,)
    _user32.IsIconic.restype = wintypes.BOOL
    _user32.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
    _user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    _user32.AttachThreadInput.argtypes = (wintypes.DWORD, wintypes.DWORD, wintypes.BOOL)
    _user32.AttachThreadInput.restype = wintypes.BOOL
    _kernel32.GetCurrentThreadId.restype = wintypes.DWORD


def foreground():
    """The window in front right now, or None."""
    if not available():
        return None
    return _user32.GetForegroundWindow() or None


def restore(target):
    """
    Bring the focus back to the window dictation started in.

    Nothing is done when the focus never moved, when there is no target, when
    the target has been closed, or when it is minimised - restoring a window
    the user put away to type into it would be worse than typing elsewhere.

    :param target: a window handle from foreground()
    :return: True if the target is in front afterwards
    """
    if not available() or not target:
        return False

    current = _user32.GetForegroundWindow()
    if current == target:
        return True
    if not _user32.IsWindow(target) or _user32.IsIconic(target):
        return False

    ours = _kernel32.GetCurrentThreadId()
    theirs = _user32.GetWindowThreadProcessId(current, None) if current else 0
    attached = bool(theirs and theirs != ours and _user32.AttachThreadInput(ours, theirs, True))
    try:
        _user32.SetForegroundWindow(target)
    finally:
        if attached:
            _user32.AttachThreadInput(ours, theirs, False)

    return _user32.GetForegroundWindow() == target
