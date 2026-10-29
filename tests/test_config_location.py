"""
Settings live outside the program folder, and old ones are carried over.

Someone who updates by unpacking a new archive in place of the old folder used
to lose every setting, because they were in src\\config.yaml inside it.
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import utils


class LocationTest(unittest.TestCase):
    def setUp(self):
        self.program = tempfile.TemporaryDirectory()
        self.settings = tempfile.TemporaryDirectory()
        self.cwd = os.getcwd()
        os.chdir(self.program.name)
        os.environ['WHISPERWRITER_CONFIG_DIR'] = os.path.join(self.settings.name, 'ww')

    def tearDown(self):
        os.chdir(self.cwd)
        del os.environ['WHISPERWRITER_CONFIG_DIR']
        self.program.cleanup()
        self.settings.cleanup()

    def test_old_settings_are_copied_once(self):
        os.makedirs('src')
        with open(utils.LEGACY_CONFIG, 'w', encoding='utf-8') as f:
            f.write('misc:\n  ui_language: ru\n')
        self.assertIn('copied', utils.move_legacy_config())
        with open(utils.config_file(), encoding='utf-8') as f:
            self.assertIn('ui_language: ru', f.read())
        self.assertTrue(os.path.isfile(utils.LEGACY_CONFIG), 'the old file stays')
        self.assertIsNone(utils.move_legacy_config(), 'done once')

    def test_nothing_to_copy(self):
        self.assertIsNone(utils.move_legacy_config())
        self.assertFalse(os.path.exists(utils.config_file()))

    def test_default_folder_is_outside_the_program(self):
        del os.environ['WHISPERWRITER_CONFIG_DIR']
        try:
            self.assertNotIn(os.path.abspath(self.program.name),
                             os.path.abspath(utils.config_dir()))
        finally:
            os.environ['WHISPERWRITER_CONFIG_DIR'] = self.settings.name


if __name__ == '__main__':
    unittest.main()
