# ВАЖНО: ctranslate2 нужно импортировать ДО PyQt5, иначе на Windows
# происходит access violation из-за конфликта нативных DLL (OpenMP/runtime).
import ctranslate2  # noqa: F401  (должен быть первым)
import faulthandler
import os
import sys
import time
from audioplayer import AudioPlayer
from pynput.keyboard import Controller
from PyQt5.QtCore import QObject, QProcess
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction, QMessageBox

import mic_gate
from key_listener import KeyListener
from result_thread import ResultThread
from ui.main_window import MainWindow
from ui.settings_window import SettingsWindow
from ui.status_window import StatusWindow
from transcription import create_local_model
from input_simulation import InputSimulator
from utils import ConfigManager


def attach_log_files():
    """
    Give print() and tracebacks somewhere to go.

    Under pythonw.exe there is no console: sys.stdout and sys.stderr are None,
    and Python drops every message and every traceback silently. Point them at
    log files in the project root instead, so a failure leaves a trace.
    Paths are derived from this file, not the working directory, so the logs
    land in the right place even if the app is started from elsewhere.
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        if sys.stdout is None:
            sys.stdout = open(os.path.join(root, 'ww_out.log'), 'a',
                              encoding='utf-8', buffering=1)
        if sys.stderr is None:
            sys.stderr = open(os.path.join(root, 'ww_err.log'), 'a',
                              encoding='utf-8', buffering=1)
    except OSError:
        # An unwritable folder must not keep the app from starting; without the
        # log files print() simply stays the no-op it was before.
        pass

    # A native crash - an access violation inside a C extension - kills the
    # process without raising anything Python can catch, so the error log stays
    # empty and the app simply vanishes. faulthandler dumps the stack of every
    # thread as the process dies, which is the only way to learn where it was.
    if sys.stderr is not None:
        try:
            faulthandler.enable(file=sys.stderr)
        except (OSError, ValueError, RuntimeError):
            pass


class WhisperWriterApp(QObject):
    def __init__(self):
        """
        Initialize the application, opening settings window if no configuration file is found.
        """
        super().__init__()
        self.error_box_open = False
        self.app = QApplication(sys.argv)
        # This app lives in the tray with every window hidden, so Qt's default
        # "quit when the last visible window closes" would end it the moment an
        # error dialog is dismissed. Quitting stays explicit: the tray menu, the
        # main window's close button, or a restart after saving settings.
        self.app.setQuitOnLastWindowClosed(False)
        self.app.setWindowIcon(QIcon(os.path.join('assets', 'ww-logo.png')))

        ConfigManager.initialize()

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

        tray_menu = QMenu()

        show_action = QAction('WhisperWriter Main Menu', self.app)
        show_action.triggered.connect(self.main_window.show)
        tray_menu.addAction(show_action)

        settings_action = QAction('Open Settings', self.app)
        settings_action.triggered.connect(self.settings_window.show)
        tray_menu.addAction(settings_action)

        exit_action = QAction('Exit', self.app)
        exit_action.triggered.connect(self.exit_app)
        tray_menu.addAction(exit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

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
            QMessageBox.information(
                self.settings_window,
                'Using Default Values',
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
            QMessageBox.warning(None, 'WhisperWriter', message)
        finally:
            self.error_box_open = False

    def on_transcription_complete(self, result):
        """
        When the transcription is complete, type the result and start listening for the activation key again.
        """
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
    print(f'--- WhisperWriter started {time.strftime("%Y-%m-%d %H:%M:%S")} ---')
    app = WhisperWriterApp()
    app.run()
