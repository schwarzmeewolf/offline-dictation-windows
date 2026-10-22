"""
Two-language interface: English and Russian.

English is the source language - every translatable string appears in the code
as its English text, and this module maps it to Russian when the Russian
interface is selected. A string with no entry falls through unchanged, so a
missing translation shows English rather than a placeholder or a crash.

The language is read from `misc.ui_language` in the config. It is separate from
`model_options.common.language`, which is the language being dictated: someone
may well dictate Russian into an English interface, or the other way round.

Widgets read their text once, when they are built, so a language change only
shows after a restart. Saving settings already restarts the app, which is the
only way the setting can change.
"""

DEFAULT_LANGUAGE = 'en'
LANGUAGES = ('en', 'ru')

_language = DEFAULT_LANGUAGE

_RUSSIAN = {
    # --- windows and menus ---
    'Settings': 'Настройки',
    'Start': 'Старт',
    'Recording...': 'Идёт запись...',
    'Transcribing...': 'Распознавание...',
    'WhisperWriter Main Menu': 'Главное меню WhisperWriter',
    'Open Settings': 'Открыть настройки',
    'Support info': 'Сведения для поддержки',
    'Could not write the support file: {error}':
        'Не удалось записать файл сведений: {error}',
    'The support file is written:\n\n{path}\n\n'
    'Send it to whoever is helping you. It holds the version, the '
    'settings without any key, the microphone and the last lines of '
    'the status log - never what you dictated.':
        'Файл сведений записан:\n\n{path}\n\n'
        'Отправьте его тому, кто вам помогает. В нём версия, настройки без '
        'ключей, микрофон и последние строки журнала работы - '
        'продиктованного текста там нет.',
    'Exit': 'Выход',
    'Dictation language': 'Язык диктовки',
    'Auto-detect': 'Определять по речи',
    'English': 'Английский',
    'Russian': 'Русский',

    # --- settings window chrome ---
    'Reset to saved settings': 'Вернуть сохранённые значения',
    'Save': 'Сохранить',
    'Browse': 'Обзор',
    'Description': 'Описание',
    'Select Whisper Model File': 'Выберите файл модели Whisper',
    'Model Files (*.bin);;All Files (*)': 'Файлы моделей (*.bin);;Все файлы (*)',
    'Settings have been saved. The application will now restart.':
        'Настройки сохранены. Программа перезапустится.',
    'Settings closed without saving. Default values are being used.':
        'Настройки закрыты без сохранения. Используются значения по умолчанию.',

    # --- tab names, from the schema's top-level keys ---
    'Model options': 'Модель',
    'Recording options': 'Запись',
    'Post processing': 'Обработка текста',
    'Misc': 'Разное',
    'Security': 'Приватность',

    # --- setting labels, from the schema's keys ---
    'Use api': 'Использовать API',
    'Language': 'Язык распознавания',
    'Temperature': 'Температура',
    'Initial prompt': 'Начальная подсказка',
    'Model': 'Модель',
    'Base url': 'Базовый URL',
    'Api key': 'Ключ API',
    'Device': 'Устройство',
    'Compute type': 'Тип вычислений',
    'Condition on previous text': 'Учитывать предыдущий текст',
    'Vad filter': 'Фильтр тишины (VAD)',
    'Model path': 'Путь к модели',
    'Activation key': 'Клавиша диктовки',
    'Input backend': 'Способ чтения клавиатуры',
    'Recording mode': 'Режим записи',
    'Sound device': 'Устройство записи',
    'Sample rate': 'Частота дискретизации',
    'Silence duration': 'Длительность паузы',
    'Min duration': 'Минимальная длительность',
    'Writing key press delay': 'Задержка между нажатиями при вводе',
    'Remove trailing period': 'Убирать точку в конце',
    'Add trailing space': 'Добавлять пробел в конце',
    'Remove capitalization': 'Приводить к нижнему регистру',
    'Input method': 'Способ ввода текста',
    'Write status log': 'Вести журнал работы',
    'Log transcribed text': 'Записывать текст диктовок в журнал',
    'Hide status window': 'Скрывать окно статуса',
    'Noise on completion': 'Звук по завершении',
    'Ui language': 'Язык интерфейса',
    'Mic gate': 'Шлюз микрофона',

    # --- setting descriptions, from the schema ---
    'Toggle to choose whether to use the OpenAI API or a local Whisper model for transcription.':
        'Выбор между OpenAI API и локальной моделью Whisper для распознавания.',
    'The language code for the transcription in ISO-639-1 format.':
        'Код языка распознавания в формате ISO-639-1.',
    'Controls the randomness of the transcription output. Lower values make the output more focused and deterministic.':
        'Управляет случайностью распознавания. Меньшие значения дают более предсказуемый результат.',
    'A string used as an initial prompt to condition the transcription. More info: https://platform.openai.com/docs/guides/speech-to-text/prompting':
        'Строка-подсказка, задающая контекст распознавания. Подробнее: '
        'https://platform.openai.com/docs/guides/speech-to-text/prompting',
    "The model to use for transcription. Currently only 'whisper-1' is available.":
        'Модель для распознавания. Сейчас доступна только «whisper-1».',
    'The base URL for the API. Can be changed to use a local API endpoint.':
        'Базовый адрес API. Можно изменить, чтобы обращаться к локальному серверу.',
    'Your API key for the OpenAI API. Required for non-local API usage.':
        'Ваш ключ OpenAI API. Нужен только при работе через API.',
    'The model to use for transcription. The larger models provide better accuracy but are slower.':
        'Модель для распознавания. Большие модели точнее, но медленнее.',
    "The device to run the local Whisper model on. Use 'cuda' for NVIDIA GPUs, 'cpu' for CPU-only processing, or 'auto' to let the system automatically choose the best available device.":
        'Устройство для локальной модели Whisper. «cuda» — видеокарта NVIDIA, «cpu» — только процессор, '
        '«auto» — выбрать доступное автоматически.',
    'The compute type to use for the local Whisper model.':
        'Тип вычислений для локальной модели Whisper.',
    'Set to true to use the previously transcribed text as a prompt for the next transcription request.':
        'Использовать ранее распознанный текст как подсказку для следующего фрагмента.',
    'Set to true to use a voice activity detection (VAD) filter to remove silence from the recording.':
        'Вырезать тишину из записи фильтром детектора речи (VAD).',
    'The path to the local Whisper model. If not specified, the default model will be downloaded.':
        'Путь к локальной модели Whisper. Если не указан, модель будет скачана.',
    "The keyboard shortcut to activate the recording and transcribing process. Separate keys with a '+'.":
        'Клавиша или сочетание, запускающее запись и распознавание. Клавиши разделяются знаком «+».',
    "The input backend to use for detecting key presses. 'auto' will try to use the best available backend.":
        'Способ отслеживания нажатий клавиш. «auto» выберет доступный автоматически.',
    'The recording mode to use. Options include continuous (auto-restart recording after pause in speech until activation key is pressed again), voice_activity_detection (stop recording after pause in speech), press_to_toggle (stop recording when activation key is pressed again), hold_to_record (stop recording when activation key is released).':
        'Режим записи. continuous — после паузы в речи запись начинается заново, пока клавишу не нажмут '
        'ещё раз; voice_activity_detection — пауза в речи завершает запись; press_to_toggle — запись '
        'останавливается повторным нажатием клавиши; hold_to_record — запись идёт, пока клавиша удерживается.',
    'The numeric index of the sound device to use for recording. To find device numbers, run `python -m sounddevice`':
        'Номер устройства записи. Список номеров покажет команда `python -m sounddevice`.',
    'The sample rate in Hz to use for recording.':
        'Частота дискретизации записи, Гц.',
    'The duration in milliseconds to wait for silence before stopping the recording.':
        'Сколько миллисекунд тишины ждать перед остановкой записи.',
    'The minimum duration in milliseconds for a recording to be processed. Recordings shorter than this will be discarded.':
        'Минимальная длительность записи в миллисекундах. Более короткие записи отбрасываются.',
    'The delay in seconds between each key press when writing the transcribed text.':
        'Задержка в секундах между нажатиями клавиш при наборе распознанного текста.',
    'Set to true to remove the trailing period from the transcribed text.':
        'Убирать точку в конце распознанного текста.',
    'Set to true to add a space to the end of the transcribed text.':
        'Добавлять пробел в конец распознанного текста.',
    'Set to true to convert the transcribed text to lowercase.':
        'Приводить распознанный текст к нижнему регистру.',
    'The method to use for simulating keyboard input.':
        'Способ имитации ввода с клавиатуры.',
    "Write what the app is doing - start-up, model, recordings, timings, errors - to ww_out.log in the program folder. Never includes what was dictated; that is log_transcribed_text. Worth keeping on: it is what to send when something goes wrong.":
        'Записывать в ww_out.log в папке программы, что она делает: запуск, модель, '
        'записи, время, ошибки. Продиктованного текста там нет никогда - для него '
        'отдельная настройка ниже. Лучше не выключать: этот файл и присылают, '
        'когда что-то сломалось.',
    "Also write every transcription, word for word, to ww_out.log. Off by default: whatever you dictate - a password, a letter, a diagnosis - would then sit on disk in plain text until the log rolls over.":
        'Записывать в ww_out.log ещё и каждый распознанный текст, слово в слово. '
        'По умолчанию выключено: всё продиктованное - пароль, письмо, диагноз - '
        'лежало бы на диске открытым текстом, пока журнал не перезапишется.',
    'Set to true to hide the status window during operation.':
        'Скрывать окно статуса во время работы.',
    'Set to true to play a noise after the transcription has been typed out.':
        'Проигрывать звук после того, как текст напечатан.',
    "Keep the microphone closed except while recording. 'consent' denies capture to all apps via Windows capability access, 'mute' only sets the endpoint mute flag, 'both' does both, 'off' disables the gate.":
        'Держать микрофон закрытым вне записи. «consent» запрещает захват всем приложениям через '
        'разрешения Windows, «mute» только выключает звук устройства, «both» — и то и другое, '
        '«off» отключает шлюз.',
    "The language of the application's own interface. Does not affect transcription - that is set by model_options.common.language.":
        'Язык интерфейса самой программы. На распознавание не влияет — за него отвечает '
        'model_options.common.language.',

    # --- messages shown when a dictation produces nothing ---
    'Nothing was recognised.': 'Ничего не распознано.',
    'Recorded {seconds:.1f} s, signal peak {peak} of 32767.':
        'Записано {seconds:.1f} с, громкость сигнала {peak} из 32767.',
    'The signal is almost flat - check the mute button on the microphone itself and the recording level in Windows sound settings.':
        'Сигнал почти нулевой — проверьте кнопку отключения звука на микрофоне '
        'и уровень записи в параметрах звука Windows.',
    'There is sound, but no words could be made out. Try speaking closer to the microphone.':
        'Звук есть, но слов в нём не разобрано. Попробуйте говорить ближе к микрофону.',
    'No speech heard - recording stopped.': 'Речь не услышана — запись остановлена.',
    'The microphone opened but nothing is coming from it. Check the mute button on the microphone itself and the recording level in Windows sound settings.':
        'Микрофон открылся, но сигнала с него нет. Проверьте кнопку отключения звука '
        'на самом микрофоне и уровень записи в параметрах звука Windows.',
    '{seconds:.0f} s without speech, signal peak {peak} of 32767':
        '{seconds:.0f} с без речи, громкость сигнала {peak} из 32767',
    'Could not start recording: the microphone is unavailable.':
        'Не удалось начать запись: микрофон недоступен.',
    'Check that it is plugged in and selected as the default recording device in Windows sound settings.':
        'Проверьте, что он подключён и выбран устройством записи по умолчанию '
        'в параметрах звука Windows.',
    'Dictation stopped: {error_type}.': 'Диктовка прервалась: {error_type}.',
    'Details are in ww_err.log in the application folder.':
        'Подробности — в файле ww_err.log в папке программы.',
}

_CATALOGUES = {'ru': _RUSSIAN}


def set_language(code):
    """
    Choose the interface language.

    :param code: a language code; anything unknown falls back to English,
                 because a typo in the config must not blank out the interface
    :return: the language actually selected
    """
    global _language
    _language = code if code in LANGUAGES else DEFAULT_LANGUAGE
    return _language


def current_language():
    """Return the active language code."""
    return _language


def tr(text):
    """
    Translate a string into the active language.

    :param text: the English source string
    :return: the translation, or the English text if there is no entry
    """
    return _CATALOGUES.get(_language, {}).get(text, text)
