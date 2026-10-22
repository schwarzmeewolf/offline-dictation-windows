"""
Tests that what was dictated stays out of the log unless asked for.

Run from the project root:

    venv\\Scripts\\python.exe -m unittest discover -s tests

Under pythonw there is no console, so everything printed lands in ww_out.log.
Every transcription used to be printed there in full, under a setting called
print_to_terminal - 85 dictated phrases, word for word, in one install's log.
The status log stays; the words need their own switch, off by default, and
configs written by older versions must not carry the old behaviour across.
"""
import contextlib
import io
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# The order main.py keeps: CTranslate2 before Qt, or its DLLs fail to load.
import cuda_libs  # noqa: E402
cuda_libs.enable()
import ctranslate2  # noqa: F401,E402

import numpy as np  # noqa: E402

import result_thread  # noqa: E402
from utils import ConfigManager  # noqa: E402

SECRET = 'my bank password is hunter2'


class MigrationTest(unittest.TestCase):
    def setUp(self):
        ConfigManager._instance = None
        ConfigManager.initialize()
        self.folder = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.folder.name, 'config.yaml')

    def tearDown(self):
        ConfigManager._instance = None
        self.folder.cleanup()

    def load(self, text):
        with open(self.path, 'w', encoding='utf-8') as file:
            file.write(text)
        ConfigManager._instance.config = ConfigManager._instance.load_default_config()
        ConfigManager._instance.load_user_config(self.path)
        return ConfigManager._instance.config['misc']

    def test_defaults_keep_the_status_log_and_drop_the_text(self):
        misc = ConfigManager._instance.load_default_config()['misc']
        self.assertTrue(misc['write_status_log'])
        self.assertFalse(misc['log_transcribed_text'])

    def test_an_old_true_does_not_turn_the_text_log_on(self):
        misc = self.load('misc:\n  print_to_terminal: true\n')
        self.assertTrue(misc['write_status_log'])
        self.assertFalse(misc['log_transcribed_text'])
        self.assertNotIn('print_to_terminal', misc)

    def test_an_old_false_still_silences_the_status_log(self):
        misc = self.load('misc:\n  print_to_terminal: false\n')
        self.assertFalse(misc['write_status_log'])

    def test_the_new_name_wins_over_the_old_one(self):
        misc = self.load('misc:\n  print_to_terminal: false\n  write_status_log: true\n')
        self.assertTrue(misc['write_status_log'])

    def test_a_saved_config_carries_only_the_new_names(self):
        self.load('misc:\n  print_to_terminal: true\n')
        ConfigManager.save_config(self.path)
        with open(self.path, encoding='utf-8') as file:
            saved = file.read()
        self.assertNotIn('print_to_terminal', saved)
        self.assertIn('write_status_log', saved)


class TranscriptionLogTest(unittest.TestCase):
    """Drive one dictation through ResultThread.run and read what it printed."""

    def setUp(self):
        ConfigManager._instance = None
        ConfigManager.initialize()

    def tearDown(self):
        ConfigManager._instance = None

    def dictate(self):
        thread = result_thread.ResultThread(local_model=object())
        audio = np.zeros(16000, dtype=np.int16)
        printed = io.StringIO()
        with mock.patch.object(thread, '_record_audio', return_value=audio), \
                mock.patch.object(result_thread, 'transcribe', return_value=SECRET + ' '), \
                contextlib.redirect_stdout(printed):
            thread.run()
        return printed.getvalue()

    def test_the_words_stay_out_by_default(self):
        log = self.dictate()
        self.assertNotIn('hunter2', log)
        self.assertIn('Transcription completed in', log)
        self.assertIn(f'{len(SECRET)} characters', log)

    def test_the_words_appear_when_asked_for(self):
        ConfigManager.set_config_value(True, 'misc', 'log_transcribed_text')
        self.assertIn(SECRET, self.dictate())


if __name__ == '__main__':
    unittest.main()
