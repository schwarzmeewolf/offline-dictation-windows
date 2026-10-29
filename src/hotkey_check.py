"""
Ask Windows whether another program has already claimed the activation key.

The listener watches keys through a hook and consumes nothing, so a
combination another program registered as a global hotkey fires in both: the
other program opens its window and takes the focus while the dictation starts.
That is how dictated text ended up in Claude's quick-entry window on a laptop
where both used Ctrl+Alt+Space.

Windows will not say who owns a hotkey, but it will refuse to register one
that is taken. So: register the combination, and release it at once if that
worked. The check sees only programs that use RegisterHotKey - one that
watches through a hook of its own, like this app, is invisible to it.

Guarded like win_focus: on any other platform the answer is UNKNOWN.
"""
import sys

from key_listener import KeyCode, MODIFIERS

FREE = 'free'
TAKEN = 'taken'
UNKNOWN = 'unknown'

_MOD_ALT, _MOD_CONTROL, _MOD_SHIFT, _MOD_WIN, _MOD_NOREPEAT = 0x1, 0x2, 0x4, 0x8, 0x4000
_MODIFIER_FLAGS = {'CTRL': _MOD_CONTROL, 'SHIFT': _MOD_SHIFT, 'ALT': _MOD_ALT, 'META': _MOD_WIN}
_ERROR_HOTKEY_ALREADY_REGISTERED = 1409
_HOTKEY_ID = 0xBF00

_VK = {KeyCode[chr(c)]: c for c in range(ord('A'), ord('Z') + 1)}
_VK.update({KeyCode[name]: ord(str(digit)) for digit, name in enumerate(
    ('ZERO', 'ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX', 'SEVEN', 'EIGHT', 'NINE'))})
_VK.update({KeyCode[f'F{n}']: 0x6F + n for n in range(1, 25)})
_VK.update({KeyCode[f'NUMPAD_{n}']: 0x60 + n for n in range(10)})
_VK.update({
    KeyCode.SPACE: 0x20, KeyCode.ENTER: 0x0D, KeyCode.TAB: 0x09,
    KeyCode.BACKSPACE: 0x08, KeyCode.ESC: 0x1B, KeyCode.INSERT: 0x2D,
    KeyCode.DELETE: 0x2E, KeyCode.HOME: 0x24, KeyCode.END: 0x23,
    KeyCode.PAGE_UP: 0x21, KeyCode.PAGE_DOWN: 0x22, KeyCode.CAPS_LOCK: 0x14,
    KeyCode.NUM_LOCK: 0x90, KeyCode.SCROLL_LOCK: 0x91, KeyCode.PAUSE: 0x13,
    KeyCode.PRINT_SCREEN: 0x2C, KeyCode.UP: 0x26, KeyCode.DOWN: 0x28,
    KeyCode.LEFT: 0x25, KeyCode.RIGHT: 0x27, KeyCode.MENU: 0x5D,
    KeyCode.NUMPAD_MULTIPLY: 0x6A, KeyCode.NUMPAD_ADD: 0x6B,
    KeyCode.NUMPAD_SUBTRACT: 0x6D, KeyCode.NUMPAD_DECIMAL: 0x6E,
    KeyCode.NUMPAD_DIVIDE: 0x6F, KeyCode.SEMICOLON: 0xBA, KeyCode.EQUALS: 0xBB,
    KeyCode.COMMA: 0xBC, KeyCode.MINUS: 0xBD, KeyCode.PERIOD: 0xBE,
    KeyCode.SLASH: 0xBF, KeyCode.BACKQUOTE: 0xC0, KeyCode.LEFT_BRACKET: 0xDB,
    KeyCode.BACKSLASH: 0xDC, KeyCode.RIGHT_BRACKET: 0xDD, KeyCode.QUOTE: 0xDE,
})


def to_hotkey(keys):
    """
    The (modifier flags, virtual key) pair RegisterHotKey takes, or None when
    the combination is not one it can express - a mouse button, a media key,
    two ordinary keys, or modifiers alone.
    """
    flags, vks = 0, []
    for key in keys:
        group = next((name for name, members in MODIFIERS.items()
                      if key == members or key in members), None)
        if group:
            flags |= _MODIFIER_FLAGS[group]
        elif key in _VK:
            vks.append(_VK[key])
        else:
            return None
    if len(vks) != 1:
        return None
    return flags, vks[0]


def check(keys):
    """
    :param keys: a parsed combination, as key_listener.parse_combination gives
    :return: FREE, TAKEN, or UNKNOWN when it cannot be asked
    """
    hotkey = to_hotkey(keys) if keys else None
    if hotkey is None or sys.platform != 'win32':
        return UNKNOWN

    import ctypes
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    flags, vk = hotkey
    if user32.RegisterHotKey(None, _HOTKEY_ID, flags | _MOD_NOREPEAT, vk):
        user32.UnregisterHotKey(None, _HOTKEY_ID)
        return FREE
    if ctypes.get_last_error() == _ERROR_HOTKEY_ALREADY_REGISTERED:
        return TAKEN
    return UNKNOWN


def describe(text):
    """
    One line for the log and the support file.

    :param text: the activation key as the config holds it
    """
    from key_listener import parse_combination
    keys, unknown = parse_combination(text or '')
    if unknown:
        return f"activation key '{text}': UNKNOWN NAME {', '.join(unknown)} - dictation is off"
    if not keys:
        return 'activation key: NOT SET - dictation is off'
    status = check(keys)
    if status == TAKEN:
        return (f"activation key '{text}': TAKEN by another program "
                f"({_ERROR_HOTKEY_ALREADY_REGISTERED})")
    if status == FREE:
        return f"activation key '{text}': free"
    return f"activation key '{text}': cannot be checked"
