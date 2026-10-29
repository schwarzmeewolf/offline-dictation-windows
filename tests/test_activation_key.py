"""
Reading the activation key, and refusing one that cannot be read in full.

An unknown name used to be dropped and the rest kept: `ctrl+alt+1` became
`ctrl+alt`, which fires on every Ctrl+Alt the user types, AltGr included, and
an empty key never fired at all without saying why.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import hotkey_check
from key_listener import (KeyChord, KeyCode, MODIFIERS, format_combination,
                          modifier_name, parse_combination)


class ParseTest(unittest.TestCase):
    def test_digits_are_read(self):
        keys, unknown = parse_combination('ctrl+alt+1')
        self.assertEqual(unknown, [])
        self.assertEqual(keys, {MODIFIERS['CTRL'], MODIFIERS['ALT'], KeyCode.ONE})

    def test_unknown_name_is_reported_not_dropped(self):
        keys, unknown = parse_combination('ctrl+alt+ф')
        self.assertEqual(unknown, ['ф'])

    def test_aliases(self):
        keys, unknown = parse_combination('Win+Escape')
        self.assertEqual(unknown, [])
        self.assertEqual(keys, {MODIFIERS['META'], KeyCode.ESC})

    def test_empty(self):
        self.assertEqual(parse_combination(''), (set(), []))

    def test_empty_chord_never_active(self):
        chord = KeyChord(set())
        self.assertFalse(chord.is_active())


class FormatTest(unittest.TestCase):
    def test_modifiers_are_generic_and_ordered(self):
        held = {modifier_name(KeyCode.ALT_RIGHT), modifier_name(KeyCode.CTRL_LEFT)}
        self.assertEqual(format_combination(held, KeyCode.SPACE), 'ctrl+alt+space')

    def test_single_key(self):
        self.assertEqual(format_combination(set(), KeyCode.PAUSE), 'pause')

    def test_round_trip(self):
        text = format_combination({'shift', 'meta'}, KeyCode.F9)
        keys, unknown = parse_combination(text)
        self.assertEqual(unknown, [])
        self.assertEqual(keys, {MODIFIERS['SHIFT'], MODIFIERS['META'], KeyCode.F9})


class HotkeyTest(unittest.TestCase):
    def test_translation(self):
        keys, _ = parse_combination('ctrl+alt+space')
        self.assertEqual(hotkey_check.to_hotkey(keys), (0x2 | 0x1, 0x20))

    def test_not_expressible(self):
        for text in ('mouse_back', 'ctrl+alt', 'a+b'):
            keys, _ = parse_combination(text)
            self.assertIsNone(hotkey_check.to_hotkey(keys), text)

    def test_describe_names_the_problem(self):
        self.assertIn('UNKNOWN NAME', hotkey_check.describe('ctrl+ф'))
        self.assertIn('NOT SET', hotkey_check.describe(''))

    @unittest.skipUnless(sys.platform == 'win32', 'Windows hotkeys')
    def test_reserved_combination_is_taken(self):
        # Windows keeps Win+Space for the input switcher on every machine.
        keys, _ = parse_combination('meta+space')
        self.assertEqual(hotkey_check.check(keys), hotkey_check.TAKEN)


if __name__ == '__main__':
    unittest.main()
