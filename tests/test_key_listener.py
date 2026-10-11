"""
Tests for the key translation in the pynput backend.

Run from the project root:

    venv\\Scripts\\python.exe -m unittest discover -s tests

These cover one defect in particular. The pynput backend used to answer
`KeyCode.SPACE` for any key it did not recognise, so an activation
combination containing the space bar fired from unrelated key combinations
that merely shared its modifiers - Ctrl+Alt+anything, because Ctrl turns a
letter into a control character the character-keyed map does not list. The
microphone opened unasked and the transcription was typed into whatever
window was in front. The defect lived for more than two years with nothing
able to catch it, which is why these tests exist.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from key_listener import InputEvent, KeyChord, KeyCode, PynputBackend


def make_backend():
    """A backend with its maps built, but no hooks installed."""
    from pynput import keyboard, mouse

    backend = PynputBackend()
    backend.keyboard = keyboard
    backend.mouse = mouse
    backend.key_map = backend._create_key_map()
    backend.vk_map = backend._create_vk_map()
    return backend


class TranslationTest(unittest.TestCase):
    def setUp(self):
        self.backend = make_backend()
        from pynput import keyboard
        self.keyboard = keyboard

    def test_known_key_is_named(self):
        key_code, event_type = self.backend._translate_key_event(
            (self.keyboard.Key.space, True))
        self.assertEqual(key_code, KeyCode.SPACE)
        self.assertEqual(event_type, InputEvent.KEY_PRESS)

    def test_unknown_key_is_nothing(self):
        """A key with no entry and no usable code must not become some other key."""
        unknown = self.keyboard.KeyCode.from_char('ю')  # Cyrillic yu
        self.assertIsNone(self.backend._resolve_key(unknown))
        self.assertEqual(self.backend._translate_key_event((unknown, True)),
                         (None, None))

    def test_unknown_key_is_not_delivered(self):
        delivered = []
        self.backend.on_input_event = delivered.append
        unknown = self.keyboard.KeyCode.from_char('ю')

        self.backend._on_keyboard_press(unknown)
        self.backend._on_keyboard_release(unknown)

        self.assertEqual(delivered, [])

    @unittest.skipUnless(sys.platform == 'win32',
                         'virtual key codes are numbered per platform')
    def test_letter_is_named_through_another_layout(self):
        """The key marked M is still M when the layout prints Cyrillic on it."""
        cyrillic = self.keyboard.KeyCode(vk=ord('M'), char='ь')
        self.assertEqual(self.backend._resolve_key(cyrillic), KeyCode.M)

    @unittest.skipUnless(sys.platform == 'win32',
                         'virtual key codes are numbered per platform')
    def test_letter_is_named_while_a_modifier_rewrites_it(self):
        """Ctrl+M arrives as a carriage return; it is still the M key."""
        with_ctrl = self.keyboard.KeyCode(vk=ord('M'), char='\r')
        self.assertEqual(self.backend._resolve_key(with_ctrl), KeyCode.M)


class ActivationTest(unittest.TestCase):
    """The defect as the user met it: a chord firing from the wrong keys."""

    def setUp(self):
        self.backend = make_backend()
        from pynput import keyboard
        self.keyboard = keyboard

        self.chord = KeyChord({
            frozenset({KeyCode.CTRL_LEFT, KeyCode.CTRL_RIGHT}),
            frozenset({KeyCode.SHIFT_LEFT, KeyCode.SHIFT_RIGHT}),
            KeyCode.SPACE,
        })
        self.activations = 0

        def handle(event):
            key, event_type = event
            was_active = self.chord.is_active()
            if self.chord.update(key, event_type) and not was_active:
                self.activations += 1

        self.backend.on_input_event = handle

    def press(self, *keys):
        for key in keys:
            self.backend._on_keyboard_press(key)

    def test_the_combination_itself_activates(self):
        self.press(self.keyboard.Key.ctrl_l,
                   self.keyboard.Key.shift_l,
                   self.keyboard.Key.space)
        self.assertEqual(self.activations, 1)

    def test_an_unknown_key_does_not_activate(self):
        self.press(self.keyboard.Key.ctrl_l,
                   self.keyboard.Key.shift_l,
                   self.keyboard.KeyCode.from_char('ю'))
        self.assertEqual(self.activations, 0)

    @unittest.skipUnless(sys.platform == 'win32',
                         'virtual key codes are numbered per platform')
    def test_a_letter_under_modifiers_does_not_activate(self):
        """Ctrl+Shift+B, as an editor would send it, is not the dictation key."""
        self.press(self.keyboard.Key.ctrl_l,
                   self.keyboard.Key.shift_l,
                   self.keyboard.KeyCode(vk=ord('B'), char='\x02'))
        self.assertEqual(self.activations, 0)


if __name__ == '__main__':
    unittest.main()
