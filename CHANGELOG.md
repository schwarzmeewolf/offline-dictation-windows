# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Fixed
- Dictation started from key combinations that were not the activation key.
  The pynput backend answered `KeyCode.SPACE` for every key it could not
  name, so an activation key containing the space bar fired from anything
  sharing its modifiers - and Ctrl alone is enough to turn a letter into a
  control character the character-keyed map does not list, which is why
  Ctrl+Shift+B from an editor opened the microphone and typed the
  transcription into whatever window was in front. Unnamed keys are now
  reported as nothing and dropped, as the evdev backend has always done.
  The default `pause` was never affected; combinations containing `space`
  were affected on every machine.

  Keys are now matched by virtual key code where the character does not
  identify them. The map is keyed by character, which is a property of the
  layout and the modifiers rather than of the key, so a letter combination
  used to stop working the moment the layout was switched to Cyrillic. On
  Windows the letter and digit keys are numbered after their ASCII
  character whatever a layout prints on them, so the key itself is now
  recognised without consulting the layout. Punctuation is left out: those
  codes move between layouts and nobody has measured which hold still.

  `tests/` is new, and holds the eight tests this needed - six of which
  fail against the old code. The defect came in with upstream's
  unreleased PR #60 (commit 139c913, August 2024) and survived two years
  because nothing could catch it.

- The application could not start on anything but Windows. `mic_gate` imported
  `winreg` at module level and `main.py` imports the gate unconditionally, so
  the very first import ended the process; `win_input` loaded user32 through
  `ctypes.WinDLL`, which does not exist elsewhere. Both are guarded now and the
  modules import anywhere. The gate reports `supported: False`, says so in the
  log when a config asks for a gate it cannot provide - believing the
  microphone is shut when it is open being the one failure worth shouting about
  - and its open, close and session calls do nothing instead of raising.
  Verified under Python 3.10 on Ubuntu 22.04.

  This restores something upstream had and this fork had taken away rather than
  adding a Linux port. There is no Linux launcher, no GPU support there, and no
  equivalent of the microphone gate; README's new "Platform support" section
  says exactly what was measured and what was only assumed.

## [2.0.1] - 2026-09-16

### Added
- Dictation language in the tray menu - auto-detect, English, Russian - taking
  effect on the next dictation. It needed neither the settings window nor a
  restart: the language is read per dictation and the multilingual model is the
  same model either way. The choice lasts for the session; the config file keeps
  the machine's usual language. The tray tooltip names the active one.

  Documented alongside it, because it surfaced by accident and is easy to
  mistake for a bug: the setting is the language Whisper *writes*, not a filter
  on what it hears. Speaking English while Russian is selected yields Russian
  text - the model translates to reach the language it was told to produce.
  Unreliable (clean audio is often transcribed as spoken instead) but real, and
  in the direction Whisper's documented translation mode does not offer, that
  mode targeting English only.
- Saving settings keeps the previous file as `config.yaml.backup-<date>`,
  five most recent. The save is wholesale, and until now nothing survived
  it.

### Fixed
- Dictated punctuation arrived as the wrong characters. Windows keyboard input
  carries a key position, not a letter, and pynput resolves a character to a
  key using the sending process's layout; the receiving window then decodes
  that position with its own. Typing into a Russian-layout window from a US
  layout turned every comma into "б" and every period into "ю", and in the
  other direction Cyrillic came out as Latin - "Hello, world." arrived as
  "Hуддщб цщкдвю". Text now goes through SendInput as Unicode, which no
  layout can reinterpret. Verified in both directions against a live window.

### Changed
- `src/config.yaml` is no longer tracked. It is written by the settings window
  and holds one machine's settings, so a tracked copy shipped the installer's
  language, model and hotkey to every clone and left that clone permanently
  modified. Defaults moved into `config_schema.yaml`, where this fork's tuned
  values now live: VAD recording with a 2 s end-of-speech pause, a single
  activation key, `int8_float32`, and no conditioning on previous text. A
  missing config file was already handled - the first run opens settings.

## [2.0.0] - 2026-09-15

First release of this fork. Numbering continues from upstream's 1.0.1 rather
than restarting; the major bump reflects changed startup behaviour and new
configuration keys, not a rewrite. Everything upstream had left unreleased is
included and listed below under "From upstream, previously unreleased".

### Added
- Microphone gate: the capture device stays shut outside of a dictation, via
  the Windows capability store and the endpoint mute flag. `tools/mic-guard.ps1`
  and a Task Scheduler backstop come with it.
- GPU transcription. `cuda_libs.py` puts the pip-installed CUDA runtime on PATH,
  without which CTranslate2 loads a model and then dies at the first encode.
- English and Russian interface, selected by `misc.ui_language`.
- Log files: under `pythonw.exe` there is no console, so `print()` and every
  traceback used to vanish. `faulthandler` is enabled for native crashes.
- Error dialogs naming the cause of a failed dictation.
- Timeouts: a recording with no speech stops after 25 s, any recording after
  five minutes.
- Windows launchers, a duplicate-instance guard and a targeted stop script.
- A version, shown in the startup log and the tray tooltip.

### Fixed
- Access violation that killed the process mid-transcription: the cyclic garbage
  collector released a COM pointer the mute lever had dropped. Pointers are now
  held for the life of the process.
- Keyboard hooks leaked on every transcription, each delivering the same key
  event again.
- Falsy configuration values were replaced by schema defaults when the settings
  window was built, and written back to disk on Save.
- A recording in voice-activity mode could not end if the microphone was silent,
  leaving the app apparently frozen.
- Error dialogs quit the application when dismissed.
- `temperature` was passed as a single number, disabling faster-whisper's retry
  on a failed decode.
- A GPU that cannot actually run now falls back to the CPU at startup rather
  than failing halfway through a dictation.

### Changed
- Starts listening on launch instead of waiting for a Start button.
- `import ctranslate2` must precede PyQt5 or Windows raises a fatal access
  violation; the order is now pinned with a comment saying so.
- `src/config.yaml` is tracked, because the settings window rewrites it whole.

### From upstream, previously unreleased

Carried over from savbell/whisper-writer, which released 1.0.1 and then
stopped with this work still unpublished.

#### Added
- New settings window to configure WhisperWriter.
- New main window to either start the keyboard listener or open the settings window.
- New continuous recording mode ([Issue #40](https://github.com/savbell/whisper-writer/issues/40)).
- New option to play a sound when transcription finishes ([Issue #40](https://github.com/savbell/whisper-writer/issues/40)).

#### Changed
- Migrated status window from using `tkinter` to `PyQt5`.
- Migrated from using JSON to using YAML to store configuration settings.
- Upgraded to latest versions of `openai` and `faster-whisper`, including support for local API ([Issue #32](https://github.com/savbell/whisper-writer/issues/32)).

#### Removed
- No longer using `keyboard` package to listen for key presses.

## [1.0.1] - 2024-01-28
### Added
- New message to identify whether Whisper was being called using the API or running locally.
- Additional hold-to-talk ([PR #28](https://github.com/savbell/whisper-writer/pull/28)) and press-to-toggle recording methods ([Issue #21](https://github.com/savbell/whisper-writer/issues/21)).
- New configuration options to:
  - Choose recording method (defaulting to voice activity detection).
  - Choose which sound device and sample rate to use.
  - Hide the status window ([PR #28](https://github.com/savbell/whisper-writer/pull/28)).

### Changed
- Migrated from `whisper` to `faster-whisper` ([Issue #11](https://github.com/savbell/whisper-writer/issues/11)).
- Migrated from `pyautogui` to `pynput` ([PR #10](https://github.com/savbell/whisper-writer/pull/10)).
- Migrated from `webrtcvad` to `webrtcvad-wheels` ([PR #17](https://github.com/savbell/whisper-writer/pull/17)).
- Changed default activation key combo from `ctrl+alt+space` to `ctrl+shift+space`.
- Changed to using a local model rather than the API by default.
- Revamped README.md, including new Roadmap, Contributing, and Credits sections.

### Fixed
- Local model is now only loaded once at start-up, rather than every time the activation key combo was pressed.
- Default configuration now auto-chooses compute type for the local model to avoid warnings.
- Graceful degradation to CPU if CUDA isn't available ([PR #30](https://github.com/savbell/whisper-writer/pull/30)).
- Removed long prefix of spaces in transcription ([PR #19](https://github.com/savbell/whisper-writer/pull/19)).

## [1.0.0] - 2023-05-29
### Added
- Initial release of WhisperWriter.
- Added CHANGELOG.md.
- Added Versioning and Known Issues to README.md.

### Changed
- Updated Whisper Python package; the local model is now compatible with Python 3.11.

[Unreleased]: https://github.com/savbell/whisper-writer/compare/v1.0.1...HEAD
[1.0.1]: https://github.com/savbell/whisper-writer/releases/tag/v1.0.0...v1.0.1
[1.0.0]: https://github.com/savbell/whisper-writer/releases/tag/v1.0.0
