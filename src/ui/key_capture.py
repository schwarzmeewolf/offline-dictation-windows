"""
A field that records the activation key by having it pressed.

The setting used to be a plain text field, and a combination such as
Ctrl+Alt+Space types no characters - so clearing the field and pressing the
keys left it empty, and the only way in was to know that the names are `ctrl`,
`alt` and `space`.

Clicking the field starts recording; the first key that is not a modifier ends
it, together with whatever modifiers are held at that moment. Esc cancels, and
so does clicking elsewhere.

The keys are read through the same hook the app listens with, not through Qt.
A combination another program registered as a hotkey never reaches a Qt
window - Windows delivers it to that program instead - and those are exactly
the combinations worth catching, because the result is checked right away
with hotkey_check and a taken one is reported. The Windows key, which the
shell keeps to itself, is seen the same way.

While a recording is in progress `capturing` is True, and the app does not
start a dictation however the keys being pressed match the current setting.
"""
from PyQt5.QtCore import QEvent, QTimer, pyqtSignal
from PyQt5.QtWidgets import QLineEdit

from i18n import tr
from key_listener import (InputEvent, KeyCode, PynputBackend, format_combination,
                          modifier_name)


class KeyCaptureEdit(QLineEdit):
    capturing = False

    # Delivered from the hook's thread; a queued signal brings it to Qt's.
    _key_event = pyqtSignal(object)
    captured = pyqtSignal(str)

    def __init__(self, value=''):
        super().__init__(value or '')
        self.setReadOnly(True)
        self._before = self.text()
        self._held = set()
        self._backend = None
        self._key_event.connect(self._on_key)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.start()

    def focusOutEvent(self, event):
        self.cancel()
        super().focusOutEvent(event)

    def event(self, event):
        # Tab would move the focus away mid-recording; the hook reports it.
        # Qt calls this while the constructor is still running, before
        # _backend exists - and an exception here ends the process.
        if getattr(self, '_backend', None) and event.type() in (QEvent.KeyPress, QEvent.ShortcutOverride):
            event.accept()
            return True
        return super().event(event)

    def start(self):
        if self._backend:
            return
        if not PynputBackend.is_available():
            self.setReadOnly(False)  # nothing to record with: let it be typed
            return
        self._before = self.text()
        self._held.clear()
        self.clear()
        self.setPlaceholderText(tr('Press the key or shortcut... Esc - cancel'))
        KeyCaptureEdit.capturing = True
        self._backend = PynputBackend()
        self._backend.watch_mouse = False
        self._backend.on_input_event = self._key_event.emit
        self._backend.start()

    def _stop(self):
        if self._backend:
            self._backend.stop()
            self._backend = None
        self.setPlaceholderText('')
        # The keys just recorded are still down, and the app's own hook sees
        # them on its thread with no ordering against this one. Hold the
        # dictation off a moment longer than it takes to let go.
        QTimer.singleShot(700, KeyCaptureEdit._release)

    @staticmethod
    def _release():
        KeyCaptureEdit.capturing = False

    def cancel(self):
        if self._backend:
            self._stop()
            self.setText(self._before)

    def _on_key(self, event):
        if not self._backend:
            return
        key, event_type = event
        modifier = modifier_name(key)
        if event_type == InputEvent.KEY_RELEASE:
            self._held.discard(modifier)
            return
        if key == KeyCode.ESC:
            self.cancel()
        elif modifier:
            self._held.add(modifier)
        else:
            text = format_combination(self._held, key)
            self._stop()
            self.setText(text)
            self.captured.emit(text)
