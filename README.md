# WhisperWriter — Windows hardening fork

Local, offline speech-to-text for Windows. Press a key, talk, stop talking — the
recognised text is typed into whatever window has focus. No internet, no account,
no audio leaves the machine.

This is a fork of **[savbell/whisper-writer](https://github.com/savbell/whisper-writer)**.
The upstream project provides the application; this fork makes it survive daily use
on Windows. Every change here came out of an actual failure, and the sections below
say which one.

---

## What this fork changes

### Failures are no longer silent

Under `pythonw.exe` there is no console, so Python sets `sys.stdout` and `sys.stderr`
to `None` and **drops every `print()` and every traceback on the floor**. A recording
that failed left no trace anywhere: the status window blinked once and nothing was
typed. It read as a crash.

- `attach_log_files()` in `src/main.py` points both streams at `ww_out.log` /
  `ww_err.log` when no console is attached. Paths are derived from the source file
  rather than the working directory, so they land correctly regardless of how the
  app was started.
- `ResultThread` gained an `errorSignal`; the app turns it into a dialog that names
  the cause — microphone unavailable, no speech heard, nothing recognised — instead
  of failing quietly.

### A recording can no longer run forever

In `voice_activity_detection` mode the only exit from the recording loop was
"speech was heard, then N ms of silence". A muted or dead microphone never raises
the speech flag, which makes that exit **unreachable** — the recording ran until the
user cancelled it by hand, and the app looked frozen.

- A recording with no speech at all now stops after 25 s and explains why.
- Any recording is capped at 5 minutes; audio captured so far is still transcribed.
- The frame wait got a timeout, so a stalled audio callback can no longer block
  `stop()` and freeze the GUI thread along with it.

### The settings window no longer corrupts falsy values

`SettingsWindow.get_config_value()` returned `ConfigManager.get_config_value(...) or
meta['value']`. Since `False or True` is `True`, **any falsy config value was replaced
by the schema default** when the widget was built — and pressing Save wrote that
default back to disk, silently flipping the setting. Replaced with an explicit
`is None` check.

### Native DLL crash on startup

`import ctranslate2` must come **before** PyQt5 in `src/main.py`, or Windows raises
a fatal access violation from conflicting native runtimes. Three lines, carrying a
comment that says not to "tidy up" the import order.

### Starts ready to use, and stops leaking hooks

Upstream shows a main window on every launch and does nothing until its **Start**
button is clicked — the dictation key is dead until then. This fork starts the key
listener as soon as the model is loaded and stays in the tray.

Doing that exposed a second problem: `PynputBackend.start()` built fresh keyboard
and mouse hooks **without stopping the previous ones**, and the app calls it again
after every transcription. Hooks accumulated for the life of the process, each one
delivering the same key event to the callbacks another time. `start()` now stops
what it started, so the count stays at two no matter how long the app runs.

### The microphone stays shut outside dictation

Windows leaves a capture device open to every process all day. This fork inverts
that: the microphone is closed by default and a dictation opens it for the few
seconds it records. Controlled by `security.mic_gate` in `src/config.yaml`
(`off`, `mute`, `consent`, `both`).

Two levers, and they are not equally strong:

| Lever | Protects against | Undone by |
| --- | --- | --- |
| `consent` — HKCU CapabilityAccessManager | browsers, meeting apps, anything opening a mic unasked | any code running as this user |
| `mute` — endpoint mute flag | accidental hot-mic; makes the state visible in the volume UI | any process, in one call |

Neither stops code that already runs as you. **The only real guarantee is the
hardware mute button on the microphone.** The gate removes the always-listening
default; it is not a defence against malware, and it would be dishonest to
present it as one.

`src/mic_gate.py` never raises: a gate that cannot close is a privacy problem,
but a gate that throws is a broken application. Failures are logged and swallowed.
The gate shuts on app start, after every recording, on exceptions during a
recording, and at exit — closed is the fail-safe direction.

Two supporting pieces live in `tools/`:

- `mic-guard.ps1` — `-Status`, `-Open`, `-Close`, `-Audit`. No administrator
  rights needed. `-Audit` reads the usage journal Windows itself keeps, showing
  which applications held the microphone and when, and which hold it right now.
  Use `-Open` when you need the microphone for a call.
- `mic-guard-task.xml` — a Task Scheduler job that closes the microphone after
  five minutes of idle, as a backstop for when WhisperWriter exits without
  restoring the state. Register with
  `schtasks /create /tn "WhisperWriter Mic Guard" /xml tools\mic-guard-task.xml /f`.
  Change the idle threshold in the XML's `<Duration>` field.

### Windows integration

- `Запустить-диктовку.bat` — launcher; refuses to start a second instance.
- `Остановить-диктовку.bat` + `stop-whisperwriter.ps1` — stops only the Python
  process running this project, matched on its command line, so other Python
  programs are never touched.
- `Отладка-диктовки.bat` — debug launcher: real console, both streams to log files,
  window stays open and prints stderr on exit.
- `src/config.yaml` is tracked in git. Upstream ignores it, but the settings window
  rewrites the whole file on Save, so version history is the only way back.

---

## Requirements

Tested on Windows 11 with **Python 3.11**. Newer Pythons may work, but 3.11 is what
this fork runs on; the dependency set below is the one known to be good.

| Package | Version |
| --- | --- |
| faster-whisper | 1.2.1 |
| ctranslate2 | 4.8.0 |
| PyQt5 | 5.15.11 |
| numpy | 1.26.4 (pinned below 2) |
| av | 17.1.0 |
| sounddevice | 0.5.5 |
| soundfile | 0.14.0 |
| pynput | 1.8.2 |
| webrtcvad-wheels | 2.0.14 |
| PyYAML | 6.0.3 |
| audioplayer | 0.6 |

Transcription runs on the CPU through CTranslate2. Neither `torch` nor `numba` is
needed. The `small` model is about 460 MB and is downloaded on first run.

## Installation

```bash
git clone <your-clone-url> whisper-writer
cd whisper-writer
py -3.11 -m venv venv
venv\Scripts\python.exe -m pip install PyQt5 faster-whisper sounddevice soundfile ^
    pynput webrtcvad-wheels PyYAML openai audioplayer python-dotenv "numpy<2"
```

Installing from `requirements.txt` may try to build `av` from source, which needs
FFmpeg toolchain; the explicit list above pulls prebuilt wheels instead.

## Running

```bash
venv\Scripts\pythonw.exe src\main.py
```

**The working directory must be the project root.** Paths in `utils.py` and
`main.py` are relative and hardcoded; started from anywhere else the app does not
fail — it silently ignores your config and opens the first-run settings window. The
launcher `.bat` files handle this with `cd /d`.

The bundled `.bat` files assume the project lives at `C:\dev\whisper-writer`. Edit
that path, or point a desktop shortcut at them with the working directory set.

It loads the model, starts listening and stays in the tray — no window to dismiss,
no button to press. The main window is still reachable from the tray menu; note
that closing it with the `×` **quits the application** rather than hiding it.

## Configuration

`src/config.yaml` overrides `src/config_schema.yaml`, which documents every option
and its allowed values. The settings in daily use here:

```yaml
model_options:
  use_api: false
  common:  { language: ru, initial_prompt: null }
  local:   { model: small, device: cpu, compute_type: int8,
             condition_on_previous_text: false, vad_filter: true }
recording_options:
  activation_key: pause
  recording_mode: voice_activity_detection
  silence_duration: 2000    # pause that ends a recording, ms
  min_duration: 100
```

Two traps worth knowing:

- **Key names come from the `KeyCode` enum in `key_listener.py`.** The Windows key
  is `meta`, not `win` or `cmd`. An unrecognised name is *not* an error — the parser
  prints `Unknown key:` and drops it from the combination, leaving a shortcut that
  quietly does the wrong thing. Since this fork writes logs, that line is now
  visible in `ww_out.log`.
- **`open()` is called without `encoding=`** when reading the schema and reading or
  writing the config. On a non-UTF-8 Windows locale this decodes as the system code
  page. Comments survive because YAML discards them after decoding, but **non-ASCII
  values would break loading.** Add `encoding='utf-8'` in `utils.py` first if you
  need one.

### Choosing an activation key

Modifier combinations collide with keyboard-layout switching more often than you
would expect. On a machine with several layouts, `Ctrl+Shift` and `Alt+Shift` are
usually the layout switchers, and Windows reserves the **entire** `Win+Space` family
for the input switcher — `RegisterHotKey` refuses `Win+Space`, `Ctrl+Win+Space` and
`Shift+Win+Space` alike, so adding a modifier does not free it. On a German layout
`Ctrl+Alt` is `AltGr`, which types `@` with `Q`, `€` with `E` and `µ` with `M`.

A bare key such as `pause` sidesteps all of it. Note also that the listener observes
keys without consuming them, so whatever you pick still reaches the focused window.

## Troubleshooting

Start with the logs — `ww_out.log` and `ww_err.log` in the project root. Each run
begins with a `--- WhisperWriter started <timestamp> ---` line.

| Symptom | Likely cause |
| --- | --- |
| Dialog: microphone unavailable | No input device. `PortAudioError: Error querying device -1` means Windows has no default recording device at all. |
| Dialog: no speech heard | The microphone is open but silent — check the hardware mute button before anything else. Windows can report a healthy level while the device sends nothing. |
| Dialog: nothing recognised | Audio arrived but produced no text. The message includes the measured peak; a near-zero peak points back at the microphone. |
| Nothing happens at all | The keyboard listener starts only after **Start** is pressed. |
| App dies instantly on start | Check that `import ctranslate2` is still the first import in `src/main.py`. |

To watch it run with a console attached:

```bash
venv\Scripts\python.exe src\main.py
```

## Credits and licence

- **[savbell/whisper-writer](https://github.com/savbell/whisper-writer)** — the
  original application, which this fork builds on. Per its README, most of the
  initial release was pair-programmed with GPT-4 and GitHub Copilot.
- [OpenAI](https://openai.com/) for the Whisper model.
- [Guillaume Klein](https://github.com/guillaumekln) and SYSTRAN for
  [faster-whisper](https://github.com/SYSTRAN/faster-whisper).

The changes in this fork were developed with Claude; the commit trailers record it.

Licensed under the **GNU General Public License v3**, inherited from upstream. See
[LICENSE](LICENSE). This is a modified version of the original project.
