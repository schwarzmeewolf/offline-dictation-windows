"""
Tests for the support file: it must carry the facts and none of the secrets.

Run from the project root:

    venv\\Scripts\\python.exe -m unittest discover -s tests

Two things must never reach a file the user is told to send to a stranger:
the OpenAI key, wherever it sits in the configuration, and the dictated text,
which the status log holds only when log_transcribed_text is on. The module
imports neither Qt nor the model, so these run bare.
"""
import io
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import support_info  # noqa: E402

KEY = 'sk-THIS-MUST-NOT-LEAK-0123456789'
DICTATED = 'my bank password is hunter2'

CONFIG = {
    'model_options': {
        'use_api': False,
        'api': {'api_key': KEY, 'base_url': 'https://api.openai.com/v1'},
        'local': {'model': 'small', 'device': 'auto'},
    },
    'misc': {'write_status_log': True, 'log_transcribed_text': True},
    'future': {'some_token': 'tok_123', 'nested': [{'client_secret': 'x'}]},
}


class SupportInfoTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.root = self.folder.name
        with io.open(os.path.join(self.root, 'ww_out.log'), 'w', encoding='utf-8') as log:
            log.write('--- WhisperWriter 9.9.9 started ---\n'
                      'Listening for the activation key.\n'
                      'Recording...\n'
                      'Transcription completed in 1.23 seconds, 27 characters.\n'
                      f'Post-processed line: {DICTATED} \n'
                      'Recording...\n')

    def tearDown(self):
        self.folder.cleanup()

    def test_the_file_is_written_where_the_dialog_says(self):
        path = support_info.write(self.root, CONFIG, '9.9.9')
        self.assertEqual(path, os.path.join(self.root, support_info.FILE_NAME))
        self.assertTrue(os.path.isfile(path))

    def test_no_secret_reaches_the_file(self):
        text = io.open(support_info.write(self.root, CONFIG, '9.9.9'),
                       encoding='utf-8').read()
        self.assertNotIn(KEY, text)
        self.assertNotIn('tok_123', text)
        self.assertNotIn("'x'", text)
        self.assertIn(support_info.REDACTED, text)

    def test_no_dictated_text_reaches_the_file(self):
        text = io.open(support_info.write(self.root, CONFIG, '9.9.9'),
                       encoding='utf-8').read()
        self.assertNotIn('hunter2', text)
        self.assertNotIn(support_info.DICTATED_MARK, text)
        # but the fact that a transcription happened, and its length, stays
        self.assertIn('Transcription completed in 1.23 seconds, 27 characters.', text)

    def test_the_facts_are_there(self):
        text = support_info.collect(self.root, CONFIG, '9.9.9')
        self.assertIn('version 9.9.9', text)
        self.assertIn('not a git checkout', text)
        self.assertIn('Python ', text)
        self.assertIn("model: 'small'", text)
        self.assertIn('Listening for the activation key.', text)

    def test_redaction_leaves_everything_else_alone(self):
        clean = support_info.redacted(CONFIG)
        self.assertEqual(clean['model_options']['local']['model'], 'small')
        self.assertEqual(clean['model_options']['api']['base_url'],
                         'https://api.openai.com/v1')
        self.assertEqual(clean['model_options']['api']['api_key'], support_info.REDACTED)
        self.assertEqual(clean['future']['nested'][0]['client_secret'], support_info.REDACTED)
        # the original is untouched
        self.assertEqual(CONFIG['model_options']['api']['api_key'], KEY)

    def test_missing_logs_do_not_stop_the_report(self):
        for name in ('ww_out.log',):
            os.remove(os.path.join(self.root, name))
        text = support_info.collect(self.root, CONFIG, '9.9.9')
        self.assertIn('(no such file)', text)
        self.assertIn('version 9.9.9', text)


if __name__ == '__main__':
    unittest.main()
