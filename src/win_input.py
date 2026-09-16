"""
Type text into the focused window as characters rather than as key positions.

Windows keyboard input carries a key *position*, not a letter: the application
receiving it decides what that position means by running it through its own
keyboard layout. pynput, asked to type a character, calls VkKeyScan to find a
key that produces it under the layout of the sending process, and - when that
key needs no modifier - injects the key. Character in, key position out.

That works only while both sides agree on the layout. They frequently do not.
Dictation types into whatever window happens to be in front, which may well be
sitting in a different layout from the one this process started in, and then:

    ','  sent from a US layout  ->  key VK_OEM_COMMA   ->  Russian window: "б"
    '.'  sent from a US layout  ->  key VK_OEM_PERIOD  ->  Russian window: "ю"

Cyrillic escapes this only by accident. VkKeyScan cannot place "п" anywhere on
a US layout, so pynput falls back to sending the character itself - the very
mechanism this module uses for everything. Which is also why the damage is
symmetric: from a Russian layout it is the Latin letters that arrive wrong.

SendInput with KEYEVENTF_UNICODE states the character and leaves no layout in
the path to reinterpret it. There is nothing to get out of step.
"""
import ctypes
import sys
import time
from ctypes import wintypes

# A pointer-sized integer. Getting this wrong silently changes the size of the
# INPUT structure, and SendInput rejects a structure whose size it does not
# recognise - it returns 0 and types nothing at all.
_ULONG_PTR = (ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8
              else ctypes.c_ulong)

_INPUT_KEYBOARD = 1
_KEYEVENTF_KEYUP = 0x0002
_KEYEVENTF_UNICODE = 0x0004
_VK_RETURN = 0x0D


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [('wVk', wintypes.WORD),
                ('wScan', wintypes.WORD),
                ('dwFlags', wintypes.DWORD),
                ('time', wintypes.DWORD),
                ('dwExtraInfo', _ULONG_PTR)]


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [('dx', wintypes.LONG),
                ('dy', wintypes.LONG),
                ('mouseData', wintypes.DWORD),
                ('dwFlags', wintypes.DWORD),
                ('time', wintypes.DWORD),
                ('dwExtraInfo', _ULONG_PTR)]


class _HARDWAREINPUT(ctypes.Structure):
    _fields_ = [('uMsg', wintypes.DWORD),
                ('wParamL', wintypes.WORD),
                ('wParamH', wintypes.WORD)]


class _INPUT(ctypes.Structure):
    class _VALUE(ctypes.Union):
        _fields_ = [('mi', _MOUSEINPUT),
                    ('ki', _KEYBDINPUT),
                    ('hi', _HARDWAREINPUT)]

    _anonymous_ = ('value',)
    _fields_ = [('type', wintypes.DWORD),
                ('value', _VALUE)]


def available():
    """Whether this module can be used on the running platform."""
    return sys.platform == 'win32'


if available():
    _user32 = ctypes.WinDLL('user32', use_last_error=True)
    _user32.SendInput.argtypes = (wintypes.UINT, ctypes.c_void_p, ctypes.c_int)
    _user32.SendInput.restype = wintypes.UINT
else:  # pragma: no cover - the module is never imported off Windows
    _user32 = None


def _char_event(code_unit, key_up):
    """One keyboard event carrying a single UTF-16 code unit."""
    event = _INPUT(type=_INPUT_KEYBOARD)
    event.ki = _KEYBDINPUT(
        wVk=0,                       # no virtual key: the character is the payload
        wScan=code_unit,
        dwFlags=_KEYEVENTF_UNICODE | (_KEYEVENTF_KEYUP if key_up else 0),
        time=0,
        dwExtraInfo=0)
    return event


def _key_event(virtual_key, key_up):
    """One keyboard event for an actual key, used where no character exists."""
    event = _INPUT(type=_INPUT_KEYBOARD)
    event.ki = _KEYBDINPUT(
        wVk=virtual_key,
        wScan=0,
        dwFlags=_KEYEVENTF_KEYUP if key_up else 0,
        time=0,
        dwExtraInfo=0)
    return event


def _events_for(char):
    """
    The press/release pair that produces one character.

    Characters outside the Basic Multilingual Plane - emoji, say - are two
    UTF-16 code units, and both have to arrive without anything in between or
    the receiving application sees two unpaired halves instead of one symbol.

    Enter is the exception to the whole scheme: U+000A is a control code, not
    something a text field inserts, so it is sent as the key it really is.
    """
    if char == '\n':
        return [_key_event(_VK_RETURN, False), _key_event(_VK_RETURN, True)]
    if char == '\r':
        return []  # a CRLF would otherwise produce two line breaks

    units = char.encode('utf-16-le')
    codes = [int.from_bytes(units[i:i + 2], 'little')
             for i in range(0, len(units), 2)]
    return ([_char_event(code, False) for code in codes] +
            [_char_event(code, True) for code in reversed(codes)])


def typewrite(text, interval=0.0):
    """
    Type text into the focused window, one character at a time.

    :param text: the text to type
    :param interval: seconds to wait between characters; some applications drop
                     input that arrives faster than they can process it
    :raises OSError: if Windows refuses the injection - which it does for a
                     window running at a higher integrity level, where no
                     simulated input works and the caller needs to know
    """
    for char in text:
        events = _events_for(char)
        if not events:
            continue

        batch = (_INPUT * len(events))(*events)
        sent = _user32.SendInput(len(events), ctypes.byref(batch),
                                 ctypes.sizeof(_INPUT))
        if sent != len(events):
            raise ctypes.WinError(ctypes.get_last_error())

        if interval:
            time.sleep(interval)
