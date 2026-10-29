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

    'Close without saving?': 'Закрыть без сохранения?',
    'Are you sure you want to close without saving?':
        'Точно закрыть, не сохранив настройки?',
    'alpha version: expect mistakes; settings and behaviour may change.':
        'альфа-версия: возможны ошибки, настройки и поведение могут меняться.',

    # --- the activation key ---
    'Press the key or shortcut... Esc - cancel':
        'Нажмите клавишу или сочетание... Esc - отмена',
    'Another program already uses {key}. Both would react to it, and '
    'the dictation could be typed into that program. Choose another key.':
        'Сочетание {key} уже занято другой программой. Отзывались бы обе, '
        'и продиктованный текст мог бы попасть в неё. Выберите другую клавишу.',
    'The activation key has a name the program does not know: '
    '{names}. Click the field and press the key instead.':
        'В клавише диктовки есть название, которого программа не знает: '
        '{names}. Щёлкните в поле и просто нажмите нужную клавишу.',
    'No activation key is set. Click the field and press the key '
    'that should start a dictation.':
        'Клавиша диктовки не задана. Щёлкните в поле и нажмите клавишу, '
        'которой будете начинать диктовку.',
    'The activation key is not set or cannot be read. Dictation '
    'is off until you set it in Settings.':
        'Клавиша диктовки не задана или записана с ошибкой. Диктовка не '
        'работает, пока вы не зададите её в настройках.',
    'Another program also uses {key}. It may open its own window '
    'and take the dictated text. Choose another key in Settings.':
        'Сочетание {key} занято ещё и другой программой. Она может открыть '
        'своё окно и забрать продиктованный текст. Выберите другую клавишу '
        'в настройках.',
    'Could not return to the window you dictated into. The text is on '
    'the clipboard: click where it should go and press Ctrl+V.':
        'Не удалось вернуться в окно, куда вы диктовали. Текст в буфере '
        'обмена: щёлкните, куда его вставить, и нажмите Ctrl+V.',

    # --- first start ---
    'Which key will start a dictation?': 'Какой клавишей начинать диктовку?',
    'Click the field and press the key. Pause is a good one if your keyboard '
    'has it; on a laptop without Pause, try Ctrl+Shift+Space. You can change '
    'it later in the settings.':
        'Щёлкните в поле и нажмите клавишу. Хорошо подходит Pause, если она '
        'есть на клавиатуре; на ноутбуке без Pause попробуйте Ctrl+Shift+Space. '
        'Потом её можно поменять в настройках.',
    'Continue': 'Дальше',

    # --- tab names, from the schema's top-level keys ---
    'Model options': 'Модель',
    'Recording options': 'Запись',
    'Post processing': 'Обработка текста',
    'Misc': 'Разное',
    'Security': 'Приватность',

    # --- setting labels, from the schema's keys ---
    'Use api': 'Использовать API',
    'Language': 'Язык диктовки',
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
    "Off: speech is recognised on this computer and never leaves it. On: the recording is sent to OpenAI's servers, which needs an internet connection and a paid OpenAI key. Leave it off unless you know you want the cloud.":
        'Выключено: речь распознаётся на этом компьютере и никуда не уходит. Включено: запись отправляется на серверы OpenAI - нужен интернет и платный ключ OpenAI. Не включайте, если не уверены, что вам нужно облако.',
    "The language you speak. Choose it here - Russian, English and so on. 'Auto-detect' lets the program guess from your speech, but it can guess wrong with an accent or with foreign words mixed in, so naming the language is more reliable. The tray menu switches it for the moment without opening the settings.":
        'Язык, на котором вы говорите. Выберите его здесь - русский, английский и так далее. «Определять по речи» - программа угадывает сама, но с акцентом или со вставками иностранных слов может ошибиться, поэтому надёжнее выбрать язык явно. В меню значка в трее язык можно сменить на время, не открывая настройки.',
    'How freely the model may guess. 0 means it always picks the most likely words, which is what dictation wants; leave it at 0 unless you have a reason. The model raises it by itself only when its first attempt is plainly garbage.':
        'Насколько свободно модель может угадывать. 0 - всегда самые вероятные слова, это и нужно для диктовки; оставьте 0, если нет особой причины. Модель сама поднимает его, только если первая попытка явно не удалась.',
    "Optional. A sentence written the way you want the result to look - for example names and terms you use often: 'Call with Anna about the VAT return in Excel.' It nudges the spelling of those words. Empty is fine.":
        'Необязательно. Фраза, написанная так, как вы хотите видеть результат, - например, имена и термины, которые вы часто произносите: «Созвон с Анной про декларацию НДС в Excel.» Помогает писать эти слова правильно. Можно оставить пустым.',
    "Only for the cloud mode. The OpenAI model to send recordings to; 'whisper-1' is the one to use.":
        'Только для облачного режима. Модель OpenAI, которой отправляются записи; нужна «whisper-1».',
    'Only for the cloud mode. The address recordings are sent to. Leave it as it is, unless you run a compatible server of your own.':
        'Только для облачного режима. Адрес, куда отправляются записи. Оставьте как есть, если у вас нет своего совместимого сервера.',
    "Only for the cloud mode. Your OpenAI key, starting with 'sk-'. It is kept in its own file beside the settings and never written to the logs or the support file.":
        'Только для облачного режима. Ваш ключ OpenAI, начинается с «sk-». Хранится в отдельном файле рядом с настройками и никогда не попадает в журналы и в файл сведений для поддержки.',
    "How big a speech model to use. Bigger is more accurate and slower. 'small' (460 MB) works on any computer. With an NVIDIA graphics card, 'large-v3' (3 GB) is both more accurate and faster. The model is downloaded once, the first time it is used. The '.en' ones understand English only.":
        'Размер модели распознавания. Больше - точнее и медленнее. «small» (460 МБ) работает на любом компьютере. С видеокартой NVIDIA «large-v3» (3 ГБ) и точнее, и быстрее. Модель скачивается один раз, при первом использовании. Модели с «.en» понимают только английский.',
    "What does the recognising. 'cpu' - the processor, works everywhere. 'cuda' - an NVIDIA graphics card, much faster, needs the GPU support the installer offers. 'auto' uses the card if it can and the processor otherwise. If the card does not work, the program says so in its log and uses the processor.":
        'Чем распознавать. «cpu» - процессором, работает везде. «cuda» - видеокартой NVIDIA, намного быстрее, нужна поддержка видеокарты, которую предлагает установщик. «auto» - видеокартой, если получится, иначе процессором. Если видеокарта не заработает, программа напишет об этом в журнал и возьмёт процессор.',
    "How precisely the model calculates. 'int8' is the fastest on a processor. 'int8_float32' works on every processor and every card. 'float16' is fastest on a newer NVIDIA card, but GTX 10-series and older cannot run it. If a choice does not work, the program falls back to the processor at start-up.":
        'Точность вычислений. «int8» - быстрее всего на процессоре. «int8_float32» работает на любом процессоре и любой видеокарте. «float16» - быстрее всего на новой видеокарте NVIDIA, но GTX 10-й серии и старше его не умеют. Если выбор не подойдёт, программа при запуске перейдёт на процессор.',
    'Show the model what it recognised just before, as a hint for the next piece. Off is better for dictation: each dictation is a separate short phrase, and with this on the model sometimes repeats itself.':
        'Показывать модели, что она распознала перед этим, как подсказку для следующего куска. Для диктовки лучше выключить: каждая диктовка - отдельная короткая фраза, а с этой настройкой модель иногда начинает повторяться.',
    'Cut the silence out of a recording before recognising it. Keeps the model from inventing words in the quiet parts. Leave it on.':
        'Вырезать тишину из записи перед распознаванием. Не даёт модели придумывать слова в паузах. Не выключайте.',
    'Optional. A folder with a model you already have on disk. Empty means the model chosen above is downloaded by itself the first time.':
        'Необязательно. Папка с моделью, которая уже есть у вас на диске. Пусто - модель, выбранная выше, скачается сама при первом запуске.',
    'The key that starts a dictation. Click the field and press the key or combination you want, for example Pause, or Ctrl+Shift+Space on a laptop without a Pause key. Esc cancels. The program warns you if another program already uses the combination - then both would react to it. The key still reaches the window you are typing in, so pick one that does nothing there.':
        'Клавиша, которая начинает диктовку. Щёлкните в поле и нажмите нужную клавишу или сочетание - например Pause, а на ноутбуке без Pause - Ctrl+Shift+Space. Esc - отмена. Если сочетание уже занято другой программой, вы увидите предупреждение: иначе на него отзывались бы обе. Нажатие доходит и до окна, в котором вы печатаете, поэтому выбирайте клавишу, которая там ничего не делает.',
    "How the program watches the keyboard. Leave it on 'auto'. 'evdev' is for Linux only.":
        'Как программа следит за клавиатурой. Оставьте «auto». «evdev» - только для Linux.',
    "When a recording stops. 'voice_activity_detection': press the key, speak, stop speaking - the recording ends by itself after a pause. 'press_to_toggle': press to start, press again to stop. 'hold_to_record': speak while holding the key down. 'continuous': after each pause a new recording starts at once, until you press the key again.":
        'Когда заканчивается запись. «voice_activity_detection»: нажали клавишу, говорите, замолчали - запись закончится сама после паузы. «press_to_toggle»: нажали - началась, нажали ещё раз - закончилась. «hold_to_record»: говорите, пока держите клавишу. «continuous»: после каждой паузы сразу начинается новая запись, пока снова не нажмёте клавишу.',
    'Which microphone to record from, by its number. Empty means the one Windows uses by default - change that in the Windows sound settings, which is easier than finding a number here.':
        'С какого микрофона записывать, по номеру. Пусто - микрофон, выбранный в Windows по умолчанию; поменять его в параметрах звука Windows проще, чем искать номер здесь.',
    'Recording quality in samples per second. The model works at 16000; leave it.':
        'Качество записи, отсчётов в секунду. Модель работает с 16000; не меняйте.',
    'How long a pause, in milliseconds, ends a recording. 2000 is two seconds - room to think in the middle of a sentence. Shorter cuts you off and splits one thought into two dictations; longer makes you wait.':
        'Сколько миллисекунд тишины заканчивают запись. 2000 - две секунды: можно подумать посреди фразы. Меньше - будет обрывать и делить одну мысль на две диктовки; больше - придётся ждать.',
    'Recordings shorter than this, in milliseconds, are thrown away - an accidental tap of the key should not produce text. 100 is a tenth of a second.':
        'Записи короче этого, в миллисекундах, выбрасываются: случайное касание клавиши не должно давать текст. 100 - десятая доля секунды.',
    'A pause between typed characters, in seconds. If some program loses letters, raise it to 0.02. Otherwise leave it.':
        'Пауза между печатаемыми буквами, в секундах. Если какая-то программа теряет буквы, поставьте 0.02. Иначе не трогайте.',
    'Drop the full stop the model puts at the end. Handy when dictating into a search box or a chat.':
        'Убирать точку, которую модель ставит в конце. Удобно для строки поиска или чата.',
    'Add a space after the text, so the next dictation does not stick to it.':
        'Добавлять пробел после текста, чтобы следующая диктовка не прилипла к нему.',
    'Write everything in small letters.':
        'Писать всё маленькими буквами.',
    "How the text is put into the window. On Windows it is 'pynput', which types the letters themselves, so the result is right whatever keyboard layout the window is in. 'ydotool' and 'dotool' are for Linux.":
        'Как текст попадает в окно. В Windows - «pynput»: печатает сами буквы, поэтому текст правильный при любой раскладке клавиатуры в окне. «ydotool» и «dotool» - для Linux.',
    "The language of the program's own windows and menus: 'en' English, 'ru' Russian. It does not change the language you dictate in - that is 'Language' on the first tab. Takes effect after saving, when the program restarts.":
        'Язык окон и меню самой программы: «en» - английский, «ru» - русский. На язык диктовки не влияет - он задаётся полем «Язык диктовки» на первой вкладке. Действует после сохранения, когда программа перезапустится.',
    'Keep a log of what the program does - start-up, model, recordings, errors - in ww_out.log in the program folder. Never what you dictated; that is the next setting. Keep it on: when something goes wrong, this log is what helps.':
        'Вести журнал того, что делает программа: запуск, модель, записи, ошибки - в файле ww_out.log в папке программы. Продиктованного текста там нет - для него следующая настройка. Не выключайте: когда что-то сломается, поможет именно этот журнал.',
    'Also write every dictation, word for word, to ww_out.log. Off by default: whatever you dictate - a password, a letter, a diagnosis - would then sit on disk as plain text.':
        'Записывать в ww_out.log ещё и каждую диктовку, слово в слово. По умолчанию выключено: всё продиктованное - пароль, письмо, диагноз - лежало бы на диске открытым текстом.',
    "Do not show the small window with 'Recording...' and 'Transcribing...' while dictating.":
        'Не показывать маленькое окно «Идёт запись...» и «Распознавание...» во время диктовки.',
    'Play a short sound when the text has been typed.':
        'Проигрывать короткий звук, когда текст напечатан.',
    "Keep the microphone shut except while you dictate. 'off' - the program does not touch it. 'mute' - mutes the microphone between dictations. 'consent' - Windows denies the microphone to every program between dictations, as if you switched it off in the privacy settings. 'both' does both. It affects all programs, video calls included, so turn it on knowingly.":
        'Держать микрофон закрытым, пока вы не диктуете. «off» - программа его не трогает. «mute» - выключает звук микрофона между диктовками. «consent» - Windows запрещает микрофон всем программам между диктовками, как выключатель в параметрах конфиденциальности. «both» - и то и другое. Действует на все программы, в том числе на видеозвонки, - включайте осознанно.',

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
