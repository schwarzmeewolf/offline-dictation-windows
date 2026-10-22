"""
One file with what a helper needs to know, and nothing they must not see.

Someone who installed the program and hit a problem cannot be asked to find
log files in a folder and read them. The tray offers "Support info" instead:
one click writes `support-info.txt` next to the program, opens the folder with
the file selected, and says to send that file to whoever is helping.

What goes in: the version, the Windows and Python versions, the versions of
the packages that matter, the settings, the default microphone, and the last
lines of the status and error logs.

What stays out, by construction rather than by care: any setting whose name
says key, token, secret or password - redacted wherever it sits in the
configuration - and any dictated text, which the status log carries only on
request, on lines marked `Post-processed line:`; those lines are dropped from
the tail whatever the setting says. The `.env` file, where the OpenAI key
lives, is never read.

This module imports nothing from Qt and nothing from the model, so the tests
can load it bare.
"""
import io
import os
import platform
import re
import subprocess
import sys
import time
from importlib import metadata

FILE_NAME = 'support-info.txt'
LOG_TAIL_LINES = 200
ERR_TAIL_LINES = 60

PACKAGES = ('faster-whisper', 'ctranslate2', 'PyQt5', 'numpy', 'sounddevice',
            'pynput', 'webrtcvad-wheels', 'PyYAML', 'pycaw',
            'nvidia-cublas-cu12', 'nvidia-cudnn-cu12')

SECRET_NAME = re.compile(r'key|token|secret|password', re.IGNORECASE)
DICTATED_MARK = 'Post-processed line:'
REDACTED = '<redacted>'


def redacted(config):
    """
    A copy of the configuration with every secret-looking value replaced.

    Matching on the key's name rather than on a fixed path means a secret
    added under a new name later is still caught, and a value that is None or
    empty is redacted too - whether a key was ever set is also not the
    helper's business.
    """
    if isinstance(config, dict):
        return {key: (REDACTED if SECRET_NAME.search(str(key)) else redacted(value))
                for key, value in config.items()}
    if isinstance(config, list):
        return [redacted(item) for item in config]
    return config


def _format(value, indent=0):
    """Settings as indented lines - readable, and with no YAML to misparse."""
    pad = '  ' * indent
    if isinstance(value, dict):
        return '\n'.join(f'{pad}{key}:' + ('\n' + _format(item, indent + 1)
                                            if isinstance(item, (dict, list))
                                            else f' {item!r}')
                         for key, item in value.items())
    if isinstance(value, list):
        return '\n'.join(f'{pad}- {item!r}' for item in value)
    return f'{pad}{value!r}'


def _git_commit(root):
    """The checked-out commit, or why there is none - a ZIP install has no .git."""
    if not os.path.isdir(os.path.join(root, '.git')):
        return 'not a git checkout'
    try:
        return subprocess.run(['git', '-C', root, 'rev-parse', '--short', 'HEAD'],
                              capture_output=True, text=True, timeout=5,
                              check=True).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return 'git not available'


def _package_versions():
    lines = []
    for name in PACKAGES:
        try:
            lines.append(f'{name} {metadata.version(name)}')
        except metadata.PackageNotFoundError:
            lines.append(f'{name} not installed')
    return lines


def _microphone():
    """The default input device as the audio library sees it."""
    try:
        import sounddevice as sd
        device = sd.query_devices(kind='input')
        return (f"{device['name']} - {device['max_input_channels']} channel(s), "
                f"{device['default_samplerate']:.0f} Hz")
    except Exception as e:  # no device, no library, no PortAudio - all worth seeing
        return f'unavailable: {e}'


def _tail(path, lines):
    """
    The last lines of a log, minus anything dictated.

    A line carrying the dictated text is dropped rather than trimmed, so a
    helper sees that a transcription happened - the 'Transcription completed'
    line before it says so, with the length - but not what it said.
    """
    if not os.path.isfile(path):
        return ['(no such file)']
    with io.open(path, encoding='utf-8', errors='replace') as file:
        kept = [line.rstrip('\n') for line in file if DICTATED_MARK not in line]
    return kept[-lines:] or ['(empty)']


def collect(root, config, version):
    """The whole report as text. Pure: nothing is written."""
    sections = [
        ('WhisperWriter', [f'version {version}', f'commit {_git_commit(root)}',
                           f'folder {root}',
                           f'written {time.strftime("%Y-%m-%d %H:%M:%S")}']),
        ('System', [platform.platform(), f'Python {sys.version.split()[0]}',
                    f'default encoding {sys.getfilesystemencoding()}']),
        ('Packages', _package_versions()),
        ('Microphone', [_microphone()]),
        ('Settings (secrets redacted)', _format(redacted(config)).split('\n')),
        (f'ww_out.log, last {LOG_TAIL_LINES} lines, dictated text removed',
         _tail(os.path.join(root, 'ww_out.log'), LOG_TAIL_LINES)),
        (f'ww_err.log, last {ERR_TAIL_LINES} lines',
         _tail(os.path.join(root, 'ww_err.log'), ERR_TAIL_LINES)),
    ]
    out = []
    for title, lines in sections:
        out.append(f'=== {title} ===')
        out.extend(lines)
        out.append('')
    return '\n'.join(out)


def write(root, config, version):
    """
    Write the report into the program folder and return its path.

    :raises OSError: if the folder cannot be written - the caller says so
    """
    path = os.path.join(root, FILE_NAME)
    with io.open(path, 'w', encoding='utf-8') as file:
        file.write(collect(root, config, version))
    return path


def reveal(path):
    """Open the folder with the file selected, where the platform can."""
    if sys.platform == 'win32':
        try:
            subprocess.Popen(['explorer', '/select,', path])
        except OSError:
            pass  # the dialog names the path anyway
