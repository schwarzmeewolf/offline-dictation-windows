# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added
- A ready-to-run Windows build. The release page carries
  `WhisperWriter-<version>-windows-x64.zip`: unpack it anywhere, double-click
  `WhisperWriter.exe`, and nothing has to be installed - not Python, not the
  components. CPU only; the speech model is still downloaded at the first
  start. Made by `tools/build-exe.ps1` from `tools/WhisperWriter.spec`, in
  the open like the installer.

### Fixed
- The voice-activity filter could refuse to load, or take the process down
  with an access violation, depending on which Visual C++ runtime got loaded
  first. The PyQt5 wheel carries its own, old copy; onnxruntime wants the
  system's newer one and is imported by faster-whisper only at the first
  transcription, long after Qt. It is now imported at startup, right after
  ctranslate2, which has the same constraint for the same reason.
- `start-dictation.bat` run before `install.bat` put up Windows' own
  "cannot find ...venv\Scripts\pythonw.exe" dialog, which told the person
  nothing about what to do. Seen in the wild on the first day the
  repository was public. Both launchers now check for the venv first and
  say, in English and Russian, to run `install.bat`.
- `debug-dictation.bat` ran the interpreter from `C:\dev\whisper-writer`
  by absolute path, so it could not have worked anywhere else. It derives
  the path from its own location now, like the other launchers.

## [2.2.0] - 2026-10-22

### Security
- What is dictated no longer goes into the log. Every transcription was
  written to `ww_out.log` in full - one install's log held 85 dictated
  phrases word for word - under `misc.print_to_terminal`, a name promising a
  terminal that `pythonw` does not have. The status log stays and now records
  each result's length instead of its text. The words have their own switch,
  `misc.log_transcribed_text`, off by default.

  `print_to_terminal` is renamed `write_status_log`. A config from an older
  version is read with the old name mapped to the new one, and the text switch
  stays off - upgrading stops the text being written rather than carrying the
  old `true` across. Both settings say plainly in the settings window, in
  English and Russian, what lands on disk.

  A failed `ydotool` call printed its whole command line, which ends in the
  dictated text; it now names the program and the exit code.

  Seven tests. Accepted on a clean install: five real dictations through the
  model left no dictated word in either log; with the switch on, all five
  appeared.

### Added
- `install.bat`, for a person who has never opened a command line. It checks
  for Python 3.11 and says where to get it if missing, refuses a folder path
  too long for Windows and says where to move the folder, builds the venv,
  installs the requirements, offers GPU support when an NVIDIA card is
  present, puts a shortcut in the Start menu and optionally in Startup. Every
  message in English and Russian. The work is in `tools/install.ps1`; the
  shortcut starts the app through `tools/launch-hidden.vbs`, so no console
  window flashes up. Accepted from a clean copy in a folder with spaces and
  Cyrillic in its name: installed in 66 s, started from the shortcut,
  refused a second copy, stopped by `stop-dictation.bat`, and left no window
  behind.
- **Support info** in the tray menu. One click writes `support-info.txt` into
  the program folder, opens the folder with the file selected, and says to
  send it to whoever is helping. It holds the version and commit, Windows
  and Python, package versions, the settings, the default microphone, and
  the last lines of the status and error logs. Every setting whose name
  says key, token, secret or password is redacted wherever it sits, and
  every `Post-processed line:` is dropped from the log tail, so neither the
  OpenAI key nor anything dictated can reach the file — six tests say so.
  The `.env` file is never read. `src/support_info.py` imports neither Qt
  nor the model.
- `DISCLAIMER.md`, in English and Russian: what you take on by using the
  program — text goes to the focused window, recognition makes mistakes, the
  microphone gate affects every application, what reaches the internet and
  what stays on disk. It is an explanation, not an agreement: GPL section 7
  allows added disclaimers only on code this fork wrote, sections 15–16
  already limit liability to what the law permits, and section 9 says nothing
  has to be accepted to run the program. README links to it at the top and
  from Installation.
- README: an "Accuracy and punctuation" section, saying that punctuation and
  capitals come from the model and what to expect from `small` on a CPU
  (counted over 85 dictations), and a "Without a command line" installation
  path.

### Fixed
- The app would not start from a folder whose path holds a character outside
  the local 8-bit code page — a Cyrillic account name was enough. Qt 5 works
  its plugin directory out for itself through that encoding, every such
  character came out as `?`, and Qt stopped the process with "no Qt platform
  plugin could be initialized" before the app's first line ran. The plugin
  path is now built in Python and handed to Qt as a string, which arrives
  intact. Found by the installer's acceptance run in `Папка с пробелом`;
  CTranslate2 loads a model from such a folder without complaint, so the
  model cache was never affected.

## [2.1.0] - 2026-10-22

### Changed
- The logs are capped. `ww_out.log` and `ww_err.log` were opened for appending
  and never trimmed, so they grew for as long as the app stayed installed. Each
  now starts over past 512 KB, on write rather than only at start-up because
  the app runs for days, and keeps the previous file as `*.log.1`.
- `faulthandler` writes to `ww_fault.log` instead of `ww_err.log`. It dumps every
  thread for each Windows exception, including the harmless RPC/COM codes
  (`0x80010012`, `0x8001010d`, `0x80010108`) the audio stack raises and handles
  itself when `sd.InputStream` opens - 21 dumps in two weeks on one machine and 25
  on another, against one real fault - so README's advice to look for
  `Windows fatal exception` in `ww_err.log` led to a file where a real crash
  could no longer be found. At the next start the real reports are moved into
  `ww_err.log` under a marked heading and the noise is dropped.
- The mouse is hooked only when the activation combination includes a mouse
  button. A global mouse hook saw every click on the machine for the whole life
  of the process, whatever the shortcut was.
- README says how to run the tests: the standard library's `unittest`, so
  nothing has to be installed for them.
- The log and fault-report code moved from `main.py` to `log_files.py`, which
  imports only the standard library and can be tested on its own.
- README no longer promises more than the app keeps. Its opening said "no
  internet", while the first run downloads the speech model, and "no audio
  leaves the machine", while an optional mode sends it to OpenAI. The
  microphone-gate section said the microphone "is closed by default", while
  the gate ships `off` - as the Configuration section correctly said. All
  three now say what happens. A Disclaimer section names the three things a
  user can actually be hurt by - text typed into whatever window has focus,
  a gate that changes a setting for every application, and the fork's
  independence from upstream and OpenAI - and points at LICENSE sections 15
  and 16 for the binding text. The install command carries the real clone URL
  instead of a placeholder.
- `tools/mic-guard-task.xml` is a template rather than one machine's
  registered task. It carried the author's computer and account name in
  `<UserId>`, an absolute path no one else has, and a description mangled
  into mojibake by an encoding mismatch - so it could not have been
  registered as shipped anyway. The account is gone, which makes Windows
  fill in whoever registers it; the path is now `__PROJECT_DIR__`, which
  README's command substitutes; the description is readable. README also
  says how to remove or disable the task, and warns that an idle trigger
  closing the microphone to every desktop application stops voice messages
  working in a chat application.

  Verified by registering the template under a temporary name: Windows
  filled in the current account and the substituted path arrived intact.

### Fixed
- Dictated text could land in a different window. The status window took the
  focus when it appeared, and on closing Windows handed the focus to the top
  window in the stack rather than back to the one it was taken from; text is
  typed wherever the focus is. Dictating into VS Code put the text into another
  application's window that was on top. The status window is now shown without
  activating and does not accept the focus, and `win_focus.py` remembers the
  window in front when the activation key is pressed and hands the focus back
  to it before typing if anything else came forward. When Windows refuses that,
  `ww_out.log` says so.
- `config.yaml` and the schema were read in the system code page - cp1251 on a
  Russian Windows - so a hand-written Russian `initial_prompt` reached the model
  as different characters, with no error to show for it. Reading and writing
  are UTF-8 now, and README's warning about it is gone. Two new tests.
- `stop-whisperwriter.ps1` meant to strip a trailing backslash with
  `TrimEnd('')` and stripped nothing. Harmless as long as the project is not in
  a drive root - but there the folder is `C:\`, and both it and
  `tools/find-running.ps1` matched processes by that substring of the command
  line, which would have stopped every Python on the drive. Both now compare
  whole paths: the interpreter in this project's `venv`, or this project's
  `src\main.py`. The stop script also stops the base interpreter the venv's
  `pythonw.exe` launches, whose command line names no folder at all.
  `find-running.ps1` had the same root trouble in another form: it trimmed the
  backslash before resolving the path, and `C:` is the current folder on drive
  C rather than its root.
- `num_lock` was listed twice in the pynput key map.
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
