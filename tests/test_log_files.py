"""
Tests for the log files kept under pythonw.exe.

Run from the project root:

    venv\\Scripts\\python.exe -m unittest discover -s tests

Two defects. The logs grew for as long as the app stayed installed, nothing
ever trimmed them. And faulthandler wrote a full dump of every thread into
ww_err.log for each harmless COM exception the audio stack raised and caught
itself - two dozen in two weeks - so the README's advice to look there for a
real crash pointed at a file where a real crash could no longer be found.
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import log_files

HARMLESS = """Windows fatal exception: code 0x80010012

Thread 0x00001234 (most recent call first):
  File "sounddevice.py", line 914 in __init__
  File "result_thread.py", line 214 in _record_audio
"""

REAL = """Windows fatal exception: access violation

Current thread 0x00005678 (most recent call first):
  File "transcription.py", line 80 in transcribe
"""


class CappedLogTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.folder.name, 'ww_out.log')

    def tearDown(self):
        self.folder.cleanup()

    def test_rolls_over_past_the_limit_and_keeps_one_previous_file(self):
        log = log_files.CappedLog(self.path, limit=1000)
        for n in range(200):
            log.write(f'line {n:04d} of the log\n')
        log.close()

        self.assertLessEqual(os.path.getsize(self.path), 1000 + 100)
        self.assertTrue(os.path.isfile(self.path + '.1'))
        self.assertLessEqual(os.path.getsize(self.path + '.1'), 1000 + 100)
        with open(self.path, encoding='utf-8') as file:
            self.assertIn('line 0199', file.read())

    def test_an_oversized_log_from_an_earlier_run_is_set_aside_at_start(self):
        with open(self.path, 'w', encoding='utf-8') as file:
            file.write('x' * 5000)
        log = log_files.CappedLog(self.path, limit=1000)
        log.write('fresh\n')
        log.close()

        with open(self.path, encoding='utf-8') as file:
            self.assertEqual(file.read(), 'fresh\n')
        self.assertEqual(os.path.getsize(self.path + '.1'), 5000)


class HarvestFaultsTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.fault_path = os.path.join(self.folder.name, 'ww_fault.log')
        self.err_path = os.path.join(self.folder.name, 'ww_err.log')

    def tearDown(self):
        self.folder.cleanup()

    def harvest(self, text):
        with open(self.fault_path, 'w', encoding='utf-8') as file:
            file.write(text)
        log = log_files.CappedLog(self.err_path)
        moved = log_files.harvest_faults(self.fault_path, log)
        log.close()
        with open(self.err_path, encoding='utf-8') as file:
            return moved, file.read()

    def test_harmless_com_codes_are_dropped(self):
        moved, err = self.harvest(HARMLESS * 3)
        self.assertEqual(moved, 0)
        self.assertNotIn('Windows fatal exception', err)

    def test_a_real_fault_is_kept_among_the_noise(self):
        moved, err = self.harvest(HARMLESS + REAL + HARMLESS)
        self.assertEqual(moved, 1)
        self.assertIn('access violation', err)
        self.assertIn('transcription.py', err)
        self.assertNotIn('0x80010012', err)

    def test_no_fault_file_is_not_an_error(self):
        log = log_files.CappedLog(self.err_path)
        self.assertEqual(log_files.harvest_faults(self.fault_path, log), 0)
        log.close()


if __name__ == '__main__':
    unittest.main()
