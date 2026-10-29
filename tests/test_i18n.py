"""
Every help text in the settings window has a Russian translation.

The translations are keyed by the English text, so editing a description in
config_schema.yaml silently orphans its translation, and the Russian interface
shows the English text from then on. That happened: the help behind the
activation key was rewritten, and a Russian user got English. This test fails
on the edit instead.
"""
import os
import sys
import unittest

import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import i18n

SCHEMA = os.path.join(os.path.dirname(__file__), '..', 'src', 'config_schema.yaml')


def settings(node, path=()):
    """(path, meta) for every setting in the schema."""
    for key, value in node.items():
        if isinstance(value, dict):
            if 'value' in value:
                yield path + (key,), value
            else:
                yield from settings(value, path + (key,))


class RussianTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(SCHEMA, encoding='utf-8') as f:
            cls.schema = yaml.safe_load(f)

    def setUp(self):
        i18n.set_language('ru')

    def tearDown(self):
        i18n.set_language('en')

    def test_every_description_is_translated(self):
        missing = [path[-1] for path, meta in settings(self.schema)
                   if i18n.tr(meta['description']) == meta['description']]
        self.assertEqual(missing, [], 'descriptions without a Russian translation')

    def test_every_label_is_translated(self):
        missing = []
        for path, _ in settings(self.schema):
            label = path[-1].replace('_', ' ').capitalize()
            if i18n.tr(label) == label:
                missing.append(label)
        self.assertEqual(missing, [], 'labels without a Russian translation')

    def test_every_tab_is_translated(self):
        missing = [key for key in self.schema
                   if i18n.tr(key.replace('_', ' ').capitalize())
                   == key.replace('_', ' ').capitalize()]
        self.assertEqual(missing, [])


if __name__ == '__main__':
    unittest.main()
