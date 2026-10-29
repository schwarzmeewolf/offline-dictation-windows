# WhisperWriter — Windows hardening fork

> **Alpha.** Expect mistakes; settings and behaviour may still change between
> releases. **Альфа-версия:** возможны ошибки, настройки и поведение могут
> меняться. [По-русски — README.ru.md](README.ru.md).

Local, offline speech-to-text for Windows. Press a key, talk, stop talking — the
recognised text is typed into whatever window has focus. No account. The first
run downloads the speech model; after that no internet is needed and no audio
leaves the machine. An optional cloud mode sends audio to OpenAI instead — it is
off unless you turn it on.

Free, as is, at your own risk: read [DISCLAIMER.md](DISCLAIMER.md) (English and
Russian) before relying on it.

This is a fork of **[savbell/whisper-writer](https://github.com/savbell/whisper-writer)**.
The upstream project provides the application; this fork makes it survive daily use
on Windows. Every change here came out of an actual failure, and the sections below
say which one — what broke, why, and how it was proved fixed.

<p align="center">
  <img src="assets/screenshot-status-en.png" alt="The status window while recording" width="320">
</p>

<p align="center">
  <img src="assets/screenshot-settings-en.png" alt="The settings window" width="620">
</p>

---

## What this fork changes

### Failures are no longer silent

Under `pythonw.exe` there is no console, so Python sets `sys.stdout` and `sys.stderr`
to `None` and **drops every `print()` and every traceback on the floor**. A recording
that failed left no trace anywhere: the status window blinked once and nothing was
typed. It read as a crash.

- `src/log_files.py` points both streams at `ww_out.log` / `ww_err.log` when no
  console is attached. Paths are derived from the source file rather than the
  working directory, so they land correctly regardless of how the app was started.
  Each log starts over past 512 KB, keeping the previous one as `*.log.1`.
- **What you dictate is not logged.** `ww_out.log` records start-up, the model,
  each recording's length and how long transcription took, the number of
  characters that came back, and errors — never the words. Every transcription
  used to be written there in full, under a setting called `print_to_terminal`
  that pointed at a terminal `pythonw` does not have. The status log is now
  `misc.write_status_log`; the words have their own switch,
  `misc.log_transcribed_text`, off by default. A config from an older version is
  read with the old name mapped to the new one, and does not switch the text on.
  An install from before this change still has the words it logged, in
  `ww_out.log` and `ww_out.log.1`; nothing deletes them for you. Delete the
  two files if you want them gone — the app starts fresh ones.
- Native crashes are caught by `faulthandler`, which writes to `ww_fault.log`.
  It reports every Windows exception, including the harmless RPC/COM ones
  (`code 0x8001xxxx`) that the audio stack raises and handles itself whenever a
  sound stream opens - two dozen in two weeks, each a full dump of every thread.
  At the next start the real reports are moved into `ww_err.log` under
  `--- faulthandler report from the previous run ---`, and the noise is dropped.
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

Windows leaves a capture device open to every process all day. This fork can
invert that: with the gate on, the microphone stays closed and a dictation opens
it for the few seconds it records. Controlled by `security.mic_gate` in
`src/config.yaml` (`off`, `mute`, `consent`, `both`). It ships `off` — closing
the microphone affects every application, so turning it on is your call; see
[Configuration](#configuration).

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

The mute lever holds its COM pointers for the life of the process and never
releases them, which is deliberate. A comtypes proxy that goes out of scope
lands in a reference cycle, so its `Release()` is left to the cyclic garbage
collector — running at an arbitrary later moment on whatever thread happens to
allocate. On this machine that release faults every time. Usually ctypes catches
it and prints an ignored `__del__` traceback; once it did not, and the collector
fired inside onnxruntime's DLL load during a transcription and took the whole
process with it. Building the device enumerator by hand instead of through
`AudioUtilities.GetMicrophone()`, and keeping every intermediate pointer alive,
leaves the collector nothing to release.

Two supporting pieces live in `tools/`:

- `mic-guard.ps1` — `-Status`, `-Open`, `-Close`, `-Audit`. No administrator
  rights needed. `-Audit` reads the usage journal Windows itself keeps, showing
  which applications held the microphone and when, and which hold it right now.
  Use `-Open` when you need the microphone for a call.
- `mic-guard-task.xml` — a Task Scheduler job that closes the microphone after
  five minutes of idle, as a backstop for when WhisperWriter exits without
  restoring the state. It is a template: `__PROJECT_DIR__` stands for the folder
  you cloned into, and the task carries no account, so registering it fills in
  whoever ran the command. From the project root:

  ```powershell
  $xml = (Get-Content tools\mic-guard-task.xml -Raw) -replace '__PROJECT_DIR__', $PWD.Path
  Register-ScheduledTask -TaskName 'WhisperWriter Mic Guard' -Xml $xml -Force
  ```

  No administrator rights needed. Change the idle threshold in the XML's
  `<Duration>` field. Remove it again with
  `Unregister-ScheduledTask -TaskName 'WhisperWriter Mic Guard'`, or keep it and
  switch it off with `Disable-ScheduledTask` — worth knowing, because an idle
  trigger that closes the microphone to every desktop application will also
  stop voice messages working in a chat application until the gate is reopened.

### Transcription runs on the GPU

Two things kept a perfectly usable GPU idle, and both failed quietly.

CTranslate2 does not link cuBLAS at load time — it asks Windows for
`cublas64_12.dll` by name at the **first encode**. When that library comes from
the `nvidia-cublas-cu12` wheel it sits inside `site-packages`, where nothing
looks for it. So the model loaded, reported success, and then died in the middle
of a transcription:

```text
RuntimeError: Library cublas64_12.dll is not found or cannot be loaded
```

`os.add_dll_directory` does not fix this — it only affects loads that opt into
the newer search flags, and CTranslate2's does not. Prepending the directories to
`PATH` does, because that is one of the places a plain `LoadLibrary` looks. That
is all `src/cuda_libs.py` is.

The second was a rule in upstream forcing `compute_type: int8` onto the CPU. It
ruled out exactly the case it was needed for: a card without usable float16 —
anything Pascal or older — is precisely where int8 is the right *GPU* choice.

A GPU that cannot actually run now falls back at startup rather than halfway
through a dictation. `create_local_model` runs a two-frame encode before handing
the model over, because constructing a CUDA model succeeds on a machine that has
a driver but no CUDA runtime; only the first encode tells the truth.

**Measured**, 29.6 s of speech, the same audio through every setup:

| Setup | Time | Speed |
| --- | --- | --- |
| large-v3, GPU, int8_float32 | 6.17 s | 4.80× realtime |
| small, GPU, int8_float32 | 1.72 s | 17.18× realtime |
| small, CPU, int8 | 7.80 s | 3.80× realtime |
| medium, GPU, int8_float32 | 10.94 s | 2.71× realtime |

On a GTX 1050 Ti — a modest card — **large-v3 on the GPU is faster than the small
model was on the CPU**, so there is no accuracy/speed trade to make.

And on 61 words of real speech through a real microphone, scored against what was
actually said:

| Setup | Errors | WER |
| --- | --- | --- |
| large-v3, GPU | 0 of 61 | 0.0 % |
| medium, GPU | 3 | 4.9 % |
| small, GPU | 5 | 8.2 % |
| small, CPU | 7 | 11.5 % |

The small model's mistakes were not near misses — it produced *сентябра*, *ворту*
and *шипелявлю*, none of which are words. `medium` is best avoided for a separate
reason: on one sample it invented a YouTube sign-off that was never spoken, a
known artefact of its training data.

### Accuracy and punctuation

Punctuation and capital letters come from the model itself. There is no
separate step that adds them, nothing to configure, and no way to make a small
model punctuate like a large one. What you get depends on the model, so the
tables above are the guide: `large-v3` on a GPU made no word errors on real
speech; `small` on a CPU — the shipped default, and all a machine without an
NVIDIA card can run at a bearable speed — made one in nine.

Punctuation follows the same curve. Counted over 85 dictations with `small` on
a CPU (`int8`) on a second machine: about two thirds of the phrases ended in a
full stop, 11 had no punctuation at all, a third of the long ones (12 words
and more) had no commas, and a few started in lower case. `large-v3` on the GPU
in this repository's measurements showed none of that. So if the text arrives
with its commas missing, the program is working as well as that model can;
the fix is a bigger model, and a bigger model wants a GPU — on a modest GTX
1050 Ti, `large-v3` ran faster than `small` did on the CPU. On a CPU alone
`large-v3` was not measured here; expect it several times slower than `small`,
and a 3 GB download.

### English and Russian interface

Upstream's interface is English only, while this fork's error messages had grown
Russian — a mix that served neither reader. Both languages now come from one
catalogue in `src/i18n.py`, chosen by `misc.ui_language` (`en` or `ru`).

English is the source language: every string appears in the code as its English
text and the catalogue maps it to Russian. A string with no entry falls through
unchanged, so a missing translation shows English rather than a blank. Labels and
help text in the settings window are translated from the English text the schema
key produces, which leaves `config_schema.yaml` untouched and easy to merge from
upstream.

Widgets read their text once, when they are built, so the language takes effect
on the next start. Saving settings already restarts the app, which is the only
way the setting can change.

<p align="center">
  <img src="assets/screenshot-status-ru.png" alt="The status window in Russian" width="320">
  &nbsp;&nbsp;
  <img src="assets/screenshot-status-en.png" alt="The status window in English" width="320">
</p>

<p align="center">
  <img src="assets/screenshot-settings-ru.png" alt="The settings window in Russian" width="620">
</p>

### Switching the dictation language, and dictating across one

The interface language and the dictated language are separate settings, and the
second one changes far more often — anyone working in two languages switches
several times a day. Upstream puts it in the settings window, where saving
restarts the application and reloads the model, which is too much ceremony to
perform between two sentences.

It is also unnecessary. `transcription.py` reads the language on every dictation
and the multilingual model is the same model whatever the answer, so the tray
menu now offers **Dictation language** — auto-detect, English, Russian — and the
next dictation obeys it. No restart, no reload, and the tray tooltip shows which
one is active. The choice lasts for the session; the config file keeps the
language this machine usually works in, and a restart returns to it.

Worth knowing, because it is easy to trip over and occasionally useful on
purpose: **this setting is the language Whisper writes in, not a filter on what
it hears.** Speak English with Russian selected and you get Russian text — the
model bridges the gap by translating. It is not a translator and makes no
promises: given clean audio it often transcribes the spoken language instead,
so treat the behaviour as available rather than reliable. Whisper's documented
translation mode only ever targets English; this is the other direction, and it
arrived by accident.

Auto-detect has its own edge: on accented speech the reported language can be
wrong while the text is right — English spoken with a Russian accent was
measured here as `ru` with probability 0.81, transcribed correctly as English.
Naming the language explicitly is the way to be certain of the output.

### Text arrives as the words that were said

Windows keyboard input carries a *key position*, not a letter — the receiving
window decides what the position means by running it through its own keyboard
layout. pynput types a character by asking `VkKeyScan` which key produces it
**under the sending process's layout**, and when that key needs no modifier it
injects the key. Character in, key position out.

The two sides agree only while they are in the same layout, and dictation types
into whatever window happens to be in front:

```
sent from a US layout, into a Russian-layout window
  "Пункт, ещё раз. Hello, world."   ->   "Пунктб ещё разю Hуддщб цщкдвю"

sent from a Russian layout, into a US-layout window
  "Пункт, ещё раз. Hello, world."   ->   "tuПeyrnj, to` hfp/ Hello, wo rld/"
```

Not a transcription error — the model had produced the sentence correctly, and
the text was mangled on its way into the window. Cyrillic survived the first
case only by accident: `VkKeyScan` cannot place "п" on a US layout, so pynput
fell back to sending the character itself. Which is what `win_input.py` now
does for everything, through `SendInput` with `KEYEVENTF_UNICODE`: the
character is the payload, and no layout is left in the path to reinterpret it.

pynput remains the fallback for other platforms, and for the case where Windows
refuses the injection outright — a window running elevated, where no simulated
input of any kind gets through. That refusal is now reported instead of
appearing as text that silently never arrives.

### Text goes to the window you dictated into

Dictating into VS Code, the text arrived in a different application whose window
happened to be on top. The status window took the focus when it appeared, and
when it closed Windows handed the focus to the top window in the stack — not back
to the one it was taken from. Text is typed wherever the focus is at that moment.

- The status window is shown without activating and does not accept the focus
  (`WA_ShowWithoutActivating`, `WindowDoesNotAcceptFocus`). Its close button still
  works: a click needs no focus.
- `win_focus.py` notes the window in front when the activation key is pressed, and
  hands the focus back to it before typing if anything else came forward during
  transcription. Windows does not always allow that; when it refuses, the text goes
  where it always went and `ww_out.log` says
  `Could not return the focus to the dictation window`. A minimised or closed
  target is left alone.

### Windows integration

- `start-dictation.bat` — launcher; refuses to start a second instance.
- `stop-dictation.bat` + `stop-whisperwriter.ps1` — stops only the Python
  process running this project, matched on its command line, so other Python
  programs are never touched.
- `debug-dictation.bat` — debug launcher: real console, both streams to log files,
  window stays open and prints stderr on exit.
- Settings are per machine and stay out of git; saving them keeps a dated backup.

---

## How it works

One dictation, end to end:

1. `key_listener.py` watches the keyboard with a low-level `pynput` hook. It
   observes rather than consumes, so the activation key still reaches whatever
   window has focus.
2. `main.py` starts a `ResultThread`. Everything below happens off the GUI
   thread, so the interface never blocks on a model.
3. `mic_gate.py` opens the microphone — lifting the Windows capability denial
   and the endpoint mute — and a `sounddevice` stream delivers 30 ms frames at
   16 kHz.
4. `result_thread.py` runs each frame past a WebRTC voice activity detector,
   counting silent frames. A long enough pause after speech ends the recording;
   so does 25 s with no speech at all, or five minutes in total.
5. The gate shuts again on the way out of the recording block, including when
   the block raises.
6. `transcription.py` hands the samples to faster-whisper — CPU or GPU — and
   post-processes the text.
7. `input_simulation.py` types the result into the focused window — as
   characters, via `win_input.py`, so the keyboard layout of that window cannot
   change what was said.

Where things live:

| File | Responsibility |
| --- | --- |
| `src/main.py` | wiring, tray icon and its language switch, error dialogs, log files |
| `src/result_thread.py` | recording loop, voice activity detection, timeouts |
| `src/transcription.py` | model creation, device fallback, decoding |
| `src/mic_gate.py` | the microphone privacy gate |
| `src/cuda_libs.py` | makes the pip-installed CUDA runtime loadable |
| `src/win_input.py` | layout-independent typing via `SendInput` |
| `src/i18n.py` | the English/Russian catalogue |
| `src/key_listener.py` | keyboard backends and shortcut parsing |
| `src/ui/` | the frameless windows and the settings form |
| `tools/` | microphone guard script and its scheduled task |

## Platform support

This is a Windows fork and Windows is where it is used and tested. Upstream was
cross-platform, and the parts this fork added had quietly taken that away: the
microphone gate imported `winreg` at module level, and `main.py` imports the
gate unconditionally, so the application stopped on its first import anywhere
else. The Windows-specific modules are now guarded and inert elsewhere.

| | Windows | Linux |
| --- | --- | --- |
| Starts, records, transcribes, types | yes | expected, not yet run end to end |
| Layout-independent typing (`win_input.py`) | yes | not needed; pynput, or ydotool on Wayland |
| Microphone gate | yes | **no** — says so in the log and stays inert |
| GPU helper (`cuda_libs.py`) | yes | no — falls back to the CPU at startup |
| Launchers | `.bat` / `.ps1` | none yet |

What was actually verified on Linux, under Python 3.10 on Ubuntu 22.04: every
module that touches Windows imports, `mic_gate` reports `supported: False` and
its open, close and session calls return without raising, `win_input.typewrite`
refuses with a clear message rather than a `NameError`, and `cuda_libs.enable()`
finds nothing and says so. The application itself has **not** been run there —
PyQt5 and CTranslate2 were not installed — so the first row above is a
reasonable expectation, not a measurement.

Three things stand between that and a working Linux version: launcher scripts,
a `ctypes.CDLL` equivalent of the CUDA helper (the dynamic loader reads
`LD_LIBRARY_PATH` at process start, so the Windows trick of editing it from
inside the process cannot work), and a microphone gate built on PipeWire, which
is a different design rather than a port — the Windows capability broker has no
counterpart.

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

Transcription runs through CTranslate2, on the CPU or on an NVIDIA GPU. Neither
`torch` nor `numba` is needed. Models are downloaded on first run: `small` is
about 460 MB, `large-v3` about 3 GB.

### For the GPU (optional)

An NVIDIA card with the CUDA 12 runtime. The runtime comes from pip, not from a
CUDA Toolkit install:

| Package | Purpose |
| --- | --- |
| nvidia-cublas-cu12 | the library CTranslate2 asks for at the first encode |
| nvidia-cudnn-cu12 | required by CTranslate2 4.5 and newer |

Check what your card supports before choosing `compute_type`:

```bash
venv\Scripts\python.exe -c "import ctranslate2; print(ctranslate2.get_supported_compute_types('cuda'))"
```

A Pascal card (GTX 10xx) will not list `float16` — use `int8_float32`. Skipping
the GPU entirely is fine; the app falls back to the CPU on its own.

## Installation

### Without installing anything

The [release page](https://github.com/schwarzmeewolf/offline-dictation-windows/releases/latest)
carries `WhisperWriter-<version>-windows-x64.zip`, a ready-to-run build.
No Python, no components, nothing goes into the system.

1. Download the archive and unpack it into a folder of your own, such as
   `C:\WhisperWriter`. Keep the folder together: `WhisperWriter.exe` needs
   the `_internal` folder beside it.
2. Double-click `WhisperWriter.exe`. Windows may put up *Windows protected
   your PC* - the program is not signed with a paid certificate, that is
   all it means. Click **More info**, then **Run anyway**.
3. First start: choose the language, press the key that will start a
   dictation, and **Save** the settings that follow - every field is filled
   in. The speech model is downloaded once (about 460 MB), and the tray icon
   appears when it is listening.

This build runs on the CPU only. For the GPU, or to change the code, install
from source as described next; the two can live side by side.

### Updating

Settings are kept in `%APPDATA%\WhisperWriter`, not in the program folder,
so a new version does not touch them.

- **Ready-to-run build:** quit the program (tray icon → Exit), delete the old
  folder, unpack the new archive in its place, start `WhisperWriter.exe`.
- **Downloaded ZIP of the source:** quit the program, unpack the new ZIP over
  the old folder, run `install.bat` again.
- **git clone:** `git pull`, then `install.bat` or `pip install -r requirements.txt`.

To hear about new versions, click **Watch → Custom → Releases** at the top of
the GitHub page. Versions up to 2.2.0 kept the settings in `src\config.yaml`
inside the program folder; the first start of a newer one copies them over.

### Without a command line

For anyone who has never opened one. Allow ten minutes and about 1 GB of
downloads — the components during the install, the speech model at the first
start.

1. **Install Python 3.11.** Download the *Windows installer (64-bit)* from
   <https://www.python.org/downloads/release/python-3119/> and run it. Leave
   the options as they are — in particular **py launcher** must stay ticked,
   it is how the installer finds Python. Newer Pythons will not do: the
   components are built for 3.11, and that is the only version tested.
2. **Get the program.** On this page click the green **Code** button, then
   **Download ZIP**. Unpack the archive into a folder with a short path, such
   as `C:\WhisperWriter`. Not the Desktop, not Downloads: Windows limits paths
   to 260 characters, the components reach 105 deep on their own, and a long
   folder name ends the install half-way with an error that says nothing
   about folders. The installer refuses to start above 140 characters and
   says so.
3. **Double-click `install.bat`.** It checks for Python, installs the
   components (about 500 MB, a few minutes), checks that they load, and puts
   **WhisperWriter** in the Start menu. If an NVIDIA card is found, it asks whether to add GPU support
   (2 GB more, faster and more accurate dictation). It asks whether to start
   with Windows, then whether to start now. Every message is shown in English
   and Russian. If something fails it says what, in both languages, and
   stops; running `install.bat` again continues where it left off.
4. **First start.** A small window asks for the language and the key that
   starts a dictation; the settings window then opens with everything filled
   in, and **Save** accepts it. The program then downloads the speech model (about 460 MB, once),
   and when the tray icon appears it is listening. Press **Pause**, speak,
   stop speaking — the text appears where the cursor is.

What `install.bat` does is nothing you could not type yourself; the script is
`tools/install.ps1`, in the open. The shortcut it creates points straight at
the program's own `pythonw.exe`, which has no console window to flash up.

Read [DISCLAIMER.md](DISCLAIMER.md) before relying on it for anything that
matters: text goes to whatever window has focus, and recognition makes
mistakes.

### From a command line

```bash
git clone https://github.com/schwarzmeewolf/offline-dictation-windows.git whisper-writer
cd whisper-writer
py -3.11 -m venv venv
venv\Scripts\python.exe -m pip install PyQt5 faster-whisper sounddevice soundfile ^
    pynput webrtcvad-wheels PyYAML openai audioplayer python-dotenv pycaw "numpy<2"
```

`requirements.txt` holds the same list and is equivalent:

```bash
venv\Scripts\python.exe -m pip install -r requirements.txt
```

It pins direct dependencies only and leaves the rest to pip. Upstream's version
pinned the entire closure, including packages this app never imports.

For GPU transcription, add:

```bash
venv\Scripts\python.exe -m pip install -r requirements-gpu.txt
```

Nothing else is needed — `src/cuda_libs.py` finds those wheels wherever pip put
them and makes them loadable.

## Running

```bash
venv\Scripts\pythonw.exe src\main.py
```

**The working directory must be the project root.** Paths in `utils.py` and
`main.py` are relative and hardcoded; started from anywhere else the app does not
fail — it silently ignores your config and opens the first-run settings window. The
launcher `.bat` files handle this with `cd /d`.

The bundled `.bat` files derive every path from their own location, so the project
can live anywhere and a desktop shortcut still works — anywhere including a
folder with spaces or Cyrillic in its name. The Start-menu shortcut that
`install.bat` creates runs `pythonw.exe src\main.py` from the project folder,
with no console window. A second start from the same folder - the shortcut
clicked twice, or the exe - finds the running copy and quietly leaves.

On first run there is no `src/config.yaml` yet, so the settings window opens;
Save writes it and restarts into it. After that the app loads the model, starts
listening and stays in the tray — no window to dismiss, no button to press. The main window is still reachable from the tray menu; note
that closing it with the `×` **quits the application** rather than hiding it.

## Configuration

There are two files, and the split matters:

| File | What it is | In git? |
| --- | --- | --- |
| `src/config_schema.yaml` | every option, its allowed values, and the default | yes |
| `%APPDATA%\WhisperWriter\config.yaml` | the settings on *this* machine | no |

`config.yaml` is written by the settings window, not by hand, and it lives
outside the program folder on purpose: replacing the program with a new
version leaves it alone, and a clone is never modified by its owner's
settings. The OpenAI key, if any, sits beside it in its own file. Up to 2.2.0
the settings were `src/config.yaml`; the first start of a newer version copies
that file over and leaves the original. `WHISPERWRITER_CONFIG_DIR` points the
app at another folder, for a portable copy on a USB stick.

A missing `config.yaml` is not an error. On first run the app asks for the
language and the activation key, then opens the settings window filled in from
the schema and those answers; Save writes the file and restarts into it.
Saving also keeps a dated copy of the previous file — `config.yaml.backup-<date>`,
five most recent — because the save is wholesale and drops anything it did not
round-trip.

The defaults are this fork's, not upstream's:

```yaml
model_options:
  local:   { model: small, device: auto, compute_type: int8_float32,
             condition_on_previous_text: false, vad_filter: true }
recording_options:
  activation_key: pause
  recording_mode: voice_activity_detection
  silence_duration: 2000    # pause that ends a recording, ms
```

Two of them are deliberately *not* set to what this machine runs:

- **`model: small`, not `large-v3`.** On a GPU, large-v3 wins on accuracy and
  speed both (see the table above) — but on a machine without one it is
  unusable, and the default has to work everywhere. Switch it in the settings
  window once you know you have a GPU.
- **`mic_gate: off`.** The gate closes the microphone for *every* application,
  not just this one. That is a system-wide change to make knowingly, so it stays
  opt-in. Turn it on in Settings → Security once you have read what it does.

Two traps worth knowing:

- **Key names come from the `KeyCode` enum in `key_listener.py`.** The settings
  window records the key by having it pressed, so the names only matter when
  editing by hand: the Windows key is `meta` (`win` is accepted too), digits are
  `one`, `two`... or `1`, `2`. A name the parser does not know turns dictation
  off rather than being dropped - dropping it used to turn `ctrl+alt+1` into
  `ctrl+alt`, which fires on every AltGr letter. The log and a tray message say
  so at start-up, and the settings window refuses to save it.
- **Save `config.yaml` as UTF-8** when editing it by hand. It is read as UTF-8
  whatever the system locale, so a Russian `initial_prompt` or a Cyrillic
  `model_path` reaches the app as written. Before 2.1.0 it was read in the system
  code page, cp1251 on a Russian Windows, and such values arrived garbled.

### Choosing an activation key

Modifier combinations collide with keyboard-layout switching more often than you
would expect. On a machine with several layouts, `Ctrl+Shift` and `Alt+Shift` are
usually the layout switchers, and Windows reserves the **entire** `Win+Space` family
for the input switcher — `RegisterHotKey` refuses `Win+Space`, `Ctrl+Win+Space` and
`Shift+Win+Space` alike, so adding a modifier does not free it. On a German layout
`Ctrl+Alt` is `AltGr`, which types `@` with `Q`, `€` with `E` and `µ` with `M`.

A bare key such as `pause` sidesteps all of it. Note also that the listener observes
keys without consuming them, so whatever you pick still reaches the focused window.

Another program may have registered the same combination as a global hotkey -
Claude for Windows takes `Ctrl+Alt+Space` for its quick-entry window. Then one
press opens that window and starts a dictation, and the text can land in the
wrong place. The app asks Windows whether the combination is taken - when the
key is recorded, and at every start - and warns if it is. Windows does not say
by whom, and it cannot see programs that watch keys through a hook, as this one
does.

## Troubleshooting

**Asking for help.** Right-click the tray icon and choose **Support info**. It
writes `support-info.txt` into the program folder, opens the folder with the
file selected, and says to send that file to whoever is helping. The file holds
the version, Windows and Python, the package versions, the settings with every
key-like value redacted, the default microphone, and the last 200 lines of the
status log with any dictated text removed — so it is safe to send to a
stranger. Nothing in it needs a programmer to produce. Then open an issue at
<https://github.com/schwarzmeewolf/offline-dictation-windows/issues/new/choose>:
the form asks what you did, what happened and what you expected, and takes the
file. That is the one place questions are read.

Start with the logs — `ww_out.log` and `ww_err.log` in the project root. Each run
begins with a `--- WhisperWriter started <timestamp> ---` line.

| Symptom | Likely cause |
| --- | --- |
| Dialog: microphone unavailable | No input device. `PortAudioError: Error querying device -1` means Windows has no default recording device at all. |
| Dialog: no speech heard | The microphone is open but silent — check the hardware mute button before anything else. Windows can report a healthy level while the device sends nothing. |
| Dialog: nothing recognised | Audio arrived but produced no text. The message includes the measured peak; a near-zero peak points back at the microphone. |
| Nothing happens at all | The model is still loading — the listener starts only once it is ready, which takes a few seconds on first launch. Check `ww_out.log` for `Listening for the activation key.` |
| App dies instantly on start | Check that `import ctranslate2` is still the first import in `src/main.py`. |
| `Library cublas64_12.dll is not found` | The CUDA wheels are missing, or `cuda_libs.enable()` did not run before the model was built. |
| Log says `Falling back to CPU` | The GPU could not complete a test encode. Transcription still works, just slower. |
| App vanishes mid-transcription | Start it again, then look in `ww_err.log` for `faulthandler report from the previous run`; the stack names the thread and the call. Before the restart the report is still in `ww_fault.log`, among harmless `code 0x8001xxxx` entries. |
| Text lands in another window, or a tray message says it is on the clipboard | When Windows refuses to bring the dictation window back, the text is not typed into whatever is in front: it goes to the clipboard, and `ww_out.log` says `Could not return the focus to the dictation window`. Paste it with Ctrl+V. If it happens often, check the activation key is not taken by another program - the log's start-up line `Activation key ...: TAKEN` says so. |
| Text typed as gibberish | On a build predating `win_input.py`, this is the keyboard-layout mismatch described above rather than a transcription error. To see what the model actually produced, turn on `misc.log_transcribed_text` for a dictation or two: `ww_out.log` then shows each result as a `Post-processed line:` - compare the two, and turn it off again. |
| Log says `Unicode input refused` | The focused window runs at a higher integrity level than this app - an elevated editor, say. No simulated input reaches it; run the app elevated too, or dictate elsewhere. |

To watch it run with a console attached:

```bash
venv\Scripts\python.exe src\main.py
```

## Tests

The tests use the standard library's `unittest`, so nothing extra needs installing.
From the project root:

```bash
venv\Scripts\python.exe -m unittest discover -s tests
```

`pytest` runs them too, if you have it.

## Versioning

Semantic versioning, continuing upstream's numbering rather than restarting:
upstream released 1.0.1 and stopped, and this fork's first release is 2.0.0. The
major bump is about changed startup behaviour and new configuration keys, not a
rewrite. `CHANGELOG.md` keeps upstream's entries below the fork's own.

The running version is in `src/version.py`, printed at the top of every run in
`ww_out.log`, and shown when hovering the tray icon — so a bug report can name
one.

## Disclaimer

The program is free and comes as is, without warranty; the binding text is
sections 15 to 17 of the [LICENSE](LICENSE). [DISCLAIMER.md](DISCLAIMER.md)
explains in plain English and Russian what that means here: text goes to
whatever window has focus, recognition makes mistakes, the microphone gate
affects every program, what reaches the internet and what stays on disk.

It is an explanation, not an agreement. It adds no terms to the GPL — section 7
would allow extra disclaimers only for code this fork added, not for upstream's,
and sections 15 and 16 already limit liability "to the extent permitted by
applicable law" — and nothing has to be accepted to run the program.

## Credits and licence

- **[savbell/whisper-writer](https://github.com/savbell/whisper-writer)** — the
  original application, which this fork builds on. Per its README, most of the
  initial release was pair-programmed with GPT-4 and GitHub Copilot.
- [OpenAI](https://openai.com/) for the Whisper model.
- [Guillaume Klein](https://github.com/guillaumekln) and SYSTRAN for
  [faster-whisper](https://github.com/SYSTRAN/faster-whisper).

The changes in this fork were developed with Claude; the commit trailers record it.

The **Sponsor** button at the top of the page goes to the maintainer of this
fork, for the work described above. The original application is savbell's; its
author asks for nothing, and this fork would not exist without it.

Licensed under the **GNU General Public License v3**, inherited from upstream. See
[LICENSE](LICENSE). This is a modified version of the original project.
