import time
import traceback
import numpy as np
import sounddevice as sd
import tempfile
import wave
import webrtcvad
from PyQt5.QtCore import QThread, QMutex, pyqtSignal
from collections import deque
from threading import Event

import mic_gate
from transcription import transcribe
from utils import ConfigManager

# A recording must not be able to run forever. The voice activity detector only
# ends a recording after it has heard speech, so a muted or unplugged microphone
# leaves the loop with no reachable exit at all - the app looks frozen.
NO_SPEECH_TIMEOUT_MS = 25000
MAX_RECORDING_MS = 300000


class NoSpeechDetected(Exception):
    """Raised when a recording ran its course without the VAD ever hearing speech."""


class ResultThread(QThread):
    """
    A thread class for handling audio recording, transcription, and result processing.

    This class manages the entire process of:
    1. Recording audio from the microphone
    2. Detecting speech and silence
    3. Saving the recorded audio as numpy array
    4. Transcribing the audio
    5. Emitting the transcription result

    Signals:
        statusSignal: Emits the current status of the thread (e.g., 'recording', 'transcribing', 'idle')
        resultSignal: Emits the transcription result
    """

    statusSignal = pyqtSignal(str)
    resultSignal = pyqtSignal(str)
    errorSignal = pyqtSignal(str)

    def __init__(self, local_model=None):
        """
        Initialize the ResultThread.

        :param local_model: Local transcription model (if applicable)
        """
        super().__init__()
        self.local_model = local_model
        self.is_recording = False
        self.is_running = True
        self.sample_rate = None
        self.mutex = QMutex()

    def stop_recording(self):
        """Stop the current recording session."""
        self.mutex.lock()
        self.is_recording = False
        self.mutex.unlock()

    def stop(self):
        """Stop the entire thread execution."""
        self.mutex.lock()
        self.is_running = False
        self.mutex.unlock()
        self.statusSignal.emit('idle')
        self.wait()

    def run(self):
        """Main execution method for the thread."""
        try:
            if not self.is_running:
                return

            self.mutex.lock()
            self.is_recording = True
            self.mutex.unlock()

            self.statusSignal.emit('recording')
            ConfigManager.console_print('Recording...')
            audio_data = self._record_audio()

            if not self.is_running:
                return

            if audio_data is None:
                self.statusSignal.emit('idle')
                return

            self.statusSignal.emit('transcribing')
            ConfigManager.console_print('Transcribing...')

            # Time the transcription process
            start_time = time.time()
            result = transcribe(audio_data, self.local_model)
            end_time = time.time()

            transcription_time = end_time - start_time
            ConfigManager.console_print(f'Transcription completed in {transcription_time:.2f} seconds. Post-processed line: {result}')

            if not self.is_running:
                return

            self.statusSignal.emit('idle')

            if not result.strip():
                # Nothing came back. Typing the lone trailing space that post
                # processing leaves behind would look like the app did its job.
                self.errorSignal.emit(self._describe_blank(audio_data))
                self.resultSignal.emit('')
                return

            self.resultSignal.emit(result)

        except Exception as e:
            traceback.print_exc()
            self.statusSignal.emit('error')
            self.errorSignal.emit(self._describe_error(e))
            self.resultSignal.emit('')
        finally:
            self.stop_recording()

    def _describe_blank(self, audio_data):
        """
        Explain a recording that came back without any text.

        :param audio_data: the recorded samples the transcriber saw
        :return: a message for the error dialog
        """
        peak = int(np.abs(audio_data).max()) if audio_data.size else 0
        seconds = audio_data.size / (self.sample_rate or 16000)
        hint = ('Сигнал почти нулевой — проверьте кнопку отключения звука на микрофоне '
                'и уровень записи в параметрах звука Windows.'
                if peak < 500 else
                'Звук есть, но слов в нём не разобрано. Попробуйте говорить ближе к микрофону.')
        return (f'Ничего не распознано.\n\n'
                f'Записано {seconds:.1f} с, громкость сигнала {peak} из 32767.\n\n{hint}')

    @staticmethod
    def _describe_error(error):
        """
        Turn an exception into something the user can act on.

        :param error: the exception raised while recording or transcribing
        :return: a message for the error dialog
        """
        if isinstance(error, NoSpeechDetected):
            return ('Речь не услышана — запись остановлена.\n\n'
                    'Микрофон открылся, но сигнала с него нет. Проверьте кнопку '
                    'отключения звука на самом микрофоне и уровень записи '
                    'в параметрах звука Windows.\n\n'
                    f'{error}')
        if isinstance(error, sd.PortAudioError):
            return ('Не удалось начать запись: микрофон недоступен.\n\n'
                    'Проверьте, что он подключён и выбран устройством записи '
                    'по умолчанию в параметрах звука Windows.\n\n'
                    f'{error}')
        return (f'Диктовка прервалась: {type(error).__name__}.\n\n'
                f'{error}\n\n'
                'Подробности — в файле ww_err.log в папке программы.')

    def _record_audio(self):
        """
        Record audio from the microphone and save it to a temporary file.

        :return: numpy array of audio data, or None if the recording is too short
        """
        recording_options = ConfigManager.get_config_section('recording_options')
        self.sample_rate = recording_options.get('sample_rate') or 16000
        frame_duration_ms = 30  # 30ms frame duration for WebRTC VAD
        frame_size = int(self.sample_rate * (frame_duration_ms / 1000.0))
        silence_duration_ms = recording_options.get('silence_duration') or 900
        silence_frames = int(silence_duration_ms / frame_duration_ms)

        # 150ms delay before starting VAD to avoid mistaking the sound of key pressing for voice
        initial_frames_to_skip = int(0.15 * self.sample_rate / frame_size)

        # Create VAD only for recording modes that use it
        recording_mode = recording_options.get('recording_mode') or 'continuous'
        vad = None
        if recording_mode in ('voice_activity_detection', 'continuous'):
            vad = webrtcvad.Vad(2)  # VAD aggressiveness: 0 to 3, 3 being the most aggressive
            speech_detected = False
            silent_frame_count = 0

        audio_buffer = deque(maxlen=frame_size)
        recording = []

        data_ready = Event()

        def audio_callback(indata, frames, time, status):
            if status:
                ConfigManager.console_print(f"Audio callback status: {status}")
            audio_buffer.extend(indata[:, 0])
            data_ready.set()

        started_at = time.time()
        gave_up_on_speech = False

        # The gate opens the microphone here and shuts it again on the way out,
        # including when the loop below raises. Outside this block the device is
        # closed to every application, this one included.
        with mic_gate.recording_session(), sd.InputStream(
                samplerate=self.sample_rate, channels=1, dtype='int16',
                blocksize=frame_size, device=recording_options.get('sound_device'),
                callback=audio_callback):
            while self.is_running and self.is_recording:
                elapsed_ms = (time.time() - started_at) * 1000

                # Silent microphone: the exit below waits for speech that will
                # never come, so stop and say so instead of recording forever.
                if vad and not speech_detected and elapsed_ms > NO_SPEECH_TIMEOUT_MS:
                    gave_up_on_speech = True
                    break

                # Heard speech but never a long enough pause - keep what we have.
                if elapsed_ms > MAX_RECORDING_MS:
                    ConfigManager.console_print('Recording hit the length limit.')
                    break

                # Waiting with a timeout keeps a stalled audio callback from
                # blocking this thread, which would freeze the whole app on stop().
                if not data_ready.wait(0.5):
                    continue
                data_ready.clear()

                if len(audio_buffer) < frame_size:
                    continue

                # Save frame
                frame = np.array(list(audio_buffer), dtype=np.int16)
                audio_buffer.clear()
                recording.extend(frame)

                # Avoid trying to detect voice in initial frames
                if initial_frames_to_skip > 0:
                    initial_frames_to_skip -= 1
                    continue

                if vad:
                    if vad.is_speech(frame.tobytes(), self.sample_rate):
                        silent_frame_count = 0
                        if not speech_detected:
                            ConfigManager.console_print("Speech detected.")
                            speech_detected = True
                    else:
                        silent_frame_count += 1

                    if speech_detected and silent_frame_count > silence_frames:
                        break

        audio_data = np.array(recording, dtype=np.int16)
        duration = len(audio_data) / self.sample_rate

        ConfigManager.console_print(f'Recording finished. Size: {audio_data.size} samples, Duration: {duration:.2f} seconds')

        if gave_up_on_speech:
            peak = int(np.abs(audio_data).max()) if audio_data.size else 0
            raise NoSpeechDetected(f'{duration:.0f} с без речи, громкость сигнала {peak} из 32767')

        min_duration_ms = recording_options.get('min_duration') or 100

        if (duration * 1000) < min_duration_ms:
            ConfigManager.console_print(f'Discarded due to being too short.')
            return None

        return audio_data
