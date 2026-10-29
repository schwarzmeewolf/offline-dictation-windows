"""
The first start: language first, then the key, then the settings.

The settings window used to be the first thing a new user met - in English,
with an empty "Language" field and a default key, Pause, that many laptops do
not have. Now a small window asks two things before it, each in a form that
needs no explaining: which language (two buttons, each in its own language),
and which key (press it). The language chosen sets both the interface and the
language dictated in; they stay separate settings, to change apart later.
"""
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QPushButton, QStackedWidget, QVBoxLayout, QWidget

import i18n
from i18n import tr
from ui.base_window import BaseWindow
from ui.key_capture import KeyCaptureEdit

BUTTON_STYLE = """
    QPushButton {
        background-color: #fff3bf;
        border: 1px solid #d9b310;
        border-radius: 6px;
        padding: 10px 24px;
        color: #3a3a3a;
        font-size: 15px;
    }
    QPushButton:hover { background-color: #ffec99; }
"""


class FirstRunWindow(BaseWindow):
    # (language code, activation key)
    chosen = pyqtSignal(str, str)

    def __init__(self, default_key):
        super().__init__('WhisperWriter', 480, 360)
        self.default_key = default_key
        self.language = None
        self.done = False
        self.pages = QStackedWidget()
        self.main_layout.addWidget(self.pages)
        self.pages.addWidget(self.language_page())

    def language_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        title = QLabel('Choose your language\nВыберите язык')
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont('Segoe UI', 13))
        layout.addStretch()
        layout.addWidget(title)
        buttons = QHBoxLayout()
        for code, name in (('en', 'English'), ('ru', 'Русский')):
            button = QPushButton(name)
            button.setStyleSheet(BUTTON_STYLE)
            button.clicked.connect(lambda _, c=code: self.pick_language(c))
            buttons.addWidget(button)
        layout.addLayout(buttons)
        layout.addStretch()
        return page

    def pick_language(self, code):
        # Everything built from here on reads its text in the new language.
        self.language = i18n.set_language(code)
        self.pages.addWidget(self.key_page())
        self.pages.setCurrentIndex(1)

    def key_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        title = QLabel(tr('Which key will start a dictation?'))
        title.setFont(QFont('Segoe UI', 12, QFont.Bold))
        title.setWordWrap(True)
        layout.addWidget(title)
        hint = QLabel(tr(
            'Click the field and press the key. Pause is a good one if your keyboard '
            'has it; on a laptop without Pause, try Ctrl+Shift+Space. You can change '
            'it later in the settings.'))
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.key_field = KeyCaptureEdit(self.default_key)
        self.key_field.setMinimumHeight(32)
        self.key_field.captured.connect(self.check_key)
        layout.addWidget(self.key_field)
        self.key_warning = QLabel('')
        self.key_warning.setWordWrap(True)
        self.key_warning.setStyleSheet('color: #a00000;')
        layout.addWidget(self.key_warning)
        layout.addStretch()
        next_button = QPushButton(tr('Continue'))
        next_button.setStyleSheet(BUTTON_STYLE)
        next_button.clicked.connect(self.finish)
        layout.addWidget(next_button)
        return page

    def check_key(self, text):
        import hotkey_check
        from key_listener import parse_combination
        keys, _ = parse_combination(text)
        taken = hotkey_check.check(keys) == hotkey_check.TAKEN
        self.key_warning.setText(tr(
            'Another program already uses {key}. Both would react to it, and the '
            'dictation could be typed into that program. Choose another key.'
        ).format(key=text) if taken else '')

    def finish(self):
        self.key_field.cancel()
        self.done = True
        self.chosen.emit(self.language, self.key_field.text() or self.default_key)
        self.close()

    def closeEvent(self, event):
        # Closed with ×: go on with whatever was chosen so far.
        self.key_field_cancel()
        if not self.done:
            self.done = True
            self.chosen.emit(self.language or i18n.current_language(), self.default_key)
        super().closeEvent(event)

    def key_field_cancel(self):
        if hasattr(self, 'key_field'):
            self.key_field.cancel()
