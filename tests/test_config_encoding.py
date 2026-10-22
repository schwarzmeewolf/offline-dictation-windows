"""
Tests for reading the configuration file as UTF-8.

Run from the project root:

    venv\\Scripts\\python.exe -m unittest discover -s tests

open() without an encoding decodes with the system code page - cp1251 on a
Russian Windows - so a hand-written Russian initial_prompt reached the model
as different characters, with no error anywhere to show for it.
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils import ConfigManager

PROMPT = 'Пример русской подсказки'


class ConfigEncodingTest(unittest.TestCase):
    def setUp(self):
        ConfigManager._instance = None
        ConfigManager.initialize()
        self.folder = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.folder.name, 'config.yaml')

    def tearDown(self):
        ConfigManager._instance = None
        self.folder.cleanup()

    def test_a_hand_written_russian_prompt_reads_back_unchanged(self):
        with open(self.path, 'w', encoding='utf-8') as file:
            file.write('model_options:\n'
                       '  common:\n'
                       f'    initial_prompt: "{PROMPT}"\n')

        ConfigManager._instance.load_user_config(self.path)

        self.assertEqual(
            ConfigManager.get_config_value('model_options', 'common', 'initial_prompt'),
            PROMPT)

    def test_a_saved_config_reads_back_unchanged(self):
        ConfigManager.set_config_value(PROMPT, 'model_options', 'common', 'initial_prompt')
        ConfigManager.save_config(self.path)

        ConfigManager._instance.config = ConfigManager._instance.load_default_config()
        ConfigManager._instance.load_user_config(self.path)

        self.assertEqual(
            ConfigManager.get_config_value('model_options', 'common', 'initial_prompt'),
            PROMPT)


if __name__ == '__main__':
    unittest.main()
