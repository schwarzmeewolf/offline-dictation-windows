# IMPORTANT: ctranslate2 must be imported BEFORE PyQt5. Both ship their own
# native runtimes, and on Windows the wrong order ends the process with an
# access violation before anything can report it. Do not tidy this away.
#
# cuda_libs comes first of all, but is not part of that constraint: it pulls in
# nothing but the standard library and only puts the CUDA directories on PATH,
# without which a GPU model dies at its first frame.
import cuda_libs
cuda_libs.enable()
import ctranslate2  # noqa: F401  (first of the native imports)
import os
import sys
import time
from audioplayer import AudioPlayer
from pynput.keyboard import Controller
import PyQt5
from PyQt5.QtCore import QCoreApplication, QObject, QProcess
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QAction, QActionGroup, QApplication, QMenu,
                             QMessageBox, QSystemTrayIcon)

import i18n
import log_files
import mic_gate
import support_info
import win_focus
from i18n import tr
from key_listener import KeyListener
from result_thread import ResultThread
from ui.main_window import MainWindow
from ui.settings_window import SettingsWindow
from ui.status_window import StatusWindow
from transcription import create_local_model
from input_simulation import InputSimulator
from utils import ConfigManager
from version import __version__


def attach_log_files():
    """
    Point the logs at the project root, whatever the working directory.

    The path is derived from this file, so the logs land in the right place
    even if the app is started from elsewhere. See log_files for the rest.
    """
    log_files.attach(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Matches the yellow BaseWindow paints, so a dialog and the status window read
# as parts of the same application. QMessageBox is a native Qt dialog rather
# than one of our own windows, so it has to be told separately; the buttons
# need their own rules too, or they keep the system grey against the yellow.
MESSAGE_BOX_STYLE = """
    QMessageBox { background-color: #ffe066; }
    QMessageBox QLabel { color: #3a3a3a; }
    QMessageBox QPushButton {
        background-color: #fff3bf;
        border: 1px solid #d9b310;
        border-radius: 4px;
        padding: 5px 20px;
        color: #3a3a3a;
    }
    QMessageBox QPushButton:hover { background-color: #ffec99; }
    QMessageBox QPushButton:pressed { background-color: #f5d949; }
"""


# Offered in the tray. The value is what Whisper is told to write, which is
# not necessarily what is being spoken: given a language, the model produces
# text in that language, translating if it has to. Speaking English with this
# set to Russian therefore yields Russian text - approximately, and with no
# guarantees, but it works often enough to be worth reaching for on purpose.
# None lets the model decide from the audio.
DICTATION_LANGUAGES = ((None, 'Auto-detect'), ('en', 'English'), ('ru', 'Russian'))


def point_qt_at_its_plugins():
    """
    Tell Qt where its plugins are, in a path it cannot garble.

    Qt 5 works its plugin directory out for itself, and on the way it pushes
    the path through the local 8-bit encoding. Any character that encoding
    cannot hold comes out as '?': installed under C:\\Users\\Юрий, Qt went
    looking in C:/Users/????/..., found no platform plugin, and stopped the
    app with "no Qt platform plugin could be initialized" before a single
    line of it ran. A Cyrillic account name or folder is enough.

    The same path built by Python and handed over as a string arrives
    intact. Has to happen before the QApplication exists.
    """
    plugins = os.path.join(os.path.dirname(PyQt5.__file__), 'Qt5', 'plugins')
    if os.path.isdir(plugins):
        QCoreApplication.setLibraryPaths([plugins])


def show_message(icon, text):
    """
    Put up a message box in the application's colours.

    :param icon: the QMessageBox icon to use
    :param text: the message to show
    """
    box = QMessageBox(icon, 'WhisperWriter', text)
    box.setStyleSheet(MESSAGE_BOX_STYLE)
    box.exec_()


class WhisperWriterApp(QObject):
    def __init__(self):
        """
        Initialize the application, opening settings window if no configuration file is found.
        """
        super().__init__()
        self.error_box_open = False
        self.dictation_target = None
        point_qt_at_its_plugins()
        self.app = QApplication(sys.argv)
        # This app lives in the tray with every window hidden, so Qt's default
        # "quit when the last visible window closes" would end it the moment an
        # error dialog is dismissed. Quitting stays explicit: the tray menu, the
        # main window's close button, or a restart after saving settings.
        self.app.setQuitOnLastWindowClosed(False)
        self.app.setWindowIcon(QIcon(os.path.join('assets', 'ww-logo.png')))

        ConfigManager.initialize()
        # Before any widget is built: they read their text once, on creation.
        i18n.set_language(ConfigManager.get_config_value('misc', 'ui_language'))

        self.settings_window = SettingsWindow()
        self.settings_window.settings_closed.connect(self.on_settings_closed)
        self.settings_window.settings_saved.connect(self.restart_app)

        if ConfigManager.config_file_exists():
            self.initialize_components()
        else:
            print('No valid configuration file found. Opening settings window...')
            self.settings_window.show()

    def initialize_components(self):
        """
        Initialize the components of the application.
        """
        self.input_simulator = InputSimulator()

        self.key_listener = KeyListener()
        self.key_listener.add_callback("on_activate", self.on_activation)
        self.key_listener.add_callback("on_deactivate", self.on_deactivation)

        model_options = ConfigManager.get_config_section('model_options')
        model_path = model_options.get('local', {}).get('model_path')
        self.local_model = create_local_model() if not model_options.get('use_api') else None

        self.result_thread = None

        self.main_window = MainWindow()
        self.main_window.openSettings.connect(self.settings_window.show)
        self.main_window.startListening.connect(self.key_listener.start)
        self.main_window.closeApp.connect(self.exit_app)

        if not ConfigManager.get_config_value('misc', 'hide_status_window'):
            self.status_window = StatusWindow()

        # Start from the closed state, so a launch never leaves the microphone
        # open just because the previous run ended badly.
        mic_gate.close()
        ConfigManager.console_print(f'Mic gate: {mic_gate.status()}')

        self.create_tray_icon()

        # Start listening straight away and stay in the tray. Upstream shows the
        # main window and waits for its Start button, which means the dictation
        # key does nothing until the user clicks it after every launch.
        self.key_listener.start()
        ConfigManager.console_print('Listening for the activation key.')

    def create_tray_icon(self):
        """
        Create the system tray icon and its context menu.
        """
        self.tray_icon = QSystemTrayIcon(QIcon(os.path.join('assets', 'ww-logo.png')), self.app)
        # Hovering the tray icon is the one place a running copy can say which
        # version it is - useful when a bug report has to name one - and which
        # language it is about to write in, which changes without any window
        # being open to show it.
        self.update_tray_tooltip()

        tray_menu = QMenu()

        show_action = QAction(tr('WhisperWriter Main Menu'), self.app)
        show_action.triggered.connect(self.main_window.show)
        tray_menu.addAction(show_action)

        self.language_menu = self.create_language_menu()
        tray_menu.addMenu(self.language_menu)

        settings_action = QAction(tr('Open Settings'), self.app)
        settings_action.triggered.connect(self.settings_window.show)
        tray_menu.addAction(settings_action)

        # For the person who installed it and cannot be asked to find the
        # logs: one click, one file, and a sentence saying whom to send it to.
        support_action = QAction(tr('Support info'), self.app)
        support_action.triggered.connect(self.write_support_info)
        tray_menu.addAction(support_action)

        exit_action = QAction(tr('Exit'), self.app)
        exit_action.triggered.connect(self.exit_app)
        tray_menu.addAction(exit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def create_language_menu(self):
        """
        Build the dictation-language submenu.

        Switching costs nothing: transcription.py reads the language on every
        dictation, and the multilingual model needs no reloading, so this does
        not go through the settings window and its restart.

        The choice lasts for the session. The config file keeps the language
        this machine usually dictates in, and a restart returns to it.
        """
        menu = QMenu(tr('Dictation language'))
        group = QActionGroup(self.app)
        group.setExclusive(True)

        current = ConfigManager.get_config_value('model_options', 'common', 'language')
        choices = list(DICTATION_LANGUAGES)
        # A language set by hand in the config - anything beyond the two this
        # interface speaks - would otherwise vanish from the menu, and picking
        # any entry would silently discard it.
        if current not in [code for code, _ in choices]:
            choices.append((current, current))

        for code, label in choices:
            action = QAction(tr(label), self.app)
            action.setCheckable(True)
            action.setChecked(code == current)
            action.triggered.connect(lambda _, c=code: self.set_dictation_language(c))
            group.addAction(action)
            menu.addAction(action)

        return menu

    def set_dictation_language(self, code):
        """
        Change the language the next dictation will be written in.

        :param code: ISO-639-1 code, or None to detect it from the audio
        """
        ConfigManager.set_config_value(code, 'model_options', 'common', 'language')
        ConfigManager.console_print(f'Dictation language: {code or "auto-detect"}')
        self.update_tray_tooltip()

    def update_tray_tooltip(self):
        """Keep the hover text showing which language is active."""
        code = ConfigManager.get_config_value('model_options', 'common', 'language')
        labels = dict(DICTATION_LANGUAGES)
        name = tr(labels[code]) if code in labels else code
        self.tray_icon.setToolTip(f'WhisperWriter {__version__} - {name}')

    def write_support_info(self):
        """Write the support file, show it in its folder, and say what to do with it."""
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        try:
            path = support_info.write(root, ConfigManager._instance.config, __version__)
        except OSError as e:
            show_message(QMessageBox.Warning,
                         tr('Could not write the support file: {error}').format(error=e))
            return
        support_info.reveal(path)
        show_message(QMessageBox.Information, tr(
            'The support file is written:\n\n{path}\n\n'
            'Send it to whoever is helping you. It holds the version, the '
            'settings without any key, the microphone and the last lines of '
            'the status log - never what you dictated.').format(path=path))

    def cleanup(self):
        mic_gate.close()
        if self.key_listener:
            self.key_listener.stop()
        if self.input_simulator:
            self.input_simulator.cleanup()

    def exit_app(self):
        """
        Exit the application.
        """
        self.cleanup()
        QApplication.quit()

    def restart_app(self):
        """Restart the application to apply the new settings."""
        self.cleanup()
        QApplication.quit()
        QProcess.startDetached(sys.executable, sys.argv)

    def on_settings_closed(self):
        """
        If settings is closed without saving on first run, initialize the components with default values.
        """
        if not os.path.exists(os.path.join('src', 'config.yaml')):
            show_message(
                QMessageBox.Information,
                'Settings closed without saving. Default values are being used.'
            )
            self.initialize_components()

    def on_activation(self):
        """
        Called when the activation key combination is pressed.
        """
        if self.result_thread and self.result_thread.isRunning():
            recording_mode = ConfigManager.get_config_value('recording_options', 'recording_mode')
            if recording_mode == 'press_to_toggle':
                self.result_thread.stop_recording()
            elif recording_mode == 'continuous':
                self.stop_result_thread()
            return

        self.start_result_thread()

    def on_deactivation(self):
        """
        Called when the activation key combination is released.
        """
        if ConfigManager.get_config_value('recording_options', 'recording_mode') == 'hold_to_record':
            if self.result_thread and self.result_thread.isRunning():
                self.result_thread.stop_recording()

    def start_result_thread(self):
        """
        Start the result thread to record audio and transcribe it.
        """
        if self.result_thread and self.result_thread.isRunning():
            return

        # The window being dictated into: whatever is in front when the key is
        # pressed, before the status window or anything else can appear.
        self.dictation_target = win_focus.foreground()

        self.result_thread = ResultThread(self.local_model)
        if not ConfigManager.get_config_value('misc', 'hide_status_window'):
            self.result_thread.statusSignal.connect(self.status_window.updateStatus)
            self.status_window.closeSignal.connect(self.stop_result_thread)
        self.result_thread.resultSignal.connect(self.on_transcription_complete)
        self.result_thread.errorSignal.connect(self.on_thread_error)
        self.result_thread.start()

    def stop_result_thread(self):
        """
        Stop the result thread.
        """
        if self.result_thread and self.result_thread.isRunning():
            self.result_thread.stop()

    def on_thread_error(self, message):
        """
        Tell the user why a dictation attempt produced nothing.

        Without this the failure is invisible: the status window blinks once and
        the traceback goes to a console that does not exist under pythonw.exe.
        One dialog at a time, so holding the activation key cannot stack them up.
        """
        if self.error_box_open:
            return
        self.error_box_open = True
        try:
            show_message(QMessageBox.Warning, message)
        finally:
            self.error_box_open = False

    def on_transcription_complete(self, result):
        """
        When the transcription is complete, type the result and start listening for the activation key again.
        """
        # Something may have come to the front while the audio was being
        # transcribed. If the dictation window cannot be brought back, the text
        # still goes out - to wherever the focus is, as it always did - but the
        # log says so, because that is the one case a user will report.
        if result and self.dictation_target and not win_focus.restore(self.dictation_target):
            print('Could not return the focus to the dictation window; '
                  'typing into the window in front.')
        self.input_simulator.typewrite(result)

        if ConfigManager.get_config_value('misc', 'noise_on_completion'):
            AudioPlayer(os.path.join('assets', 'beep.wav')).play(block=True)

        if ConfigManager.get_config_value('recording_options', 'recording_mode') == 'continuous':
            self.start_result_thread()
        else:
            self.key_listener.start()

    def run(self):
        """
        Start the application.
        """
        sys.exit(self.app.exec_())


if __name__ == '__main__':
    attach_log_files()
    print(f'--- WhisperWriter {__version__} started '
          f'{time.strftime("%Y-%m-%d %H:%M:%S")} ---')
    app = WhisperWriterApp()
    app.run()
