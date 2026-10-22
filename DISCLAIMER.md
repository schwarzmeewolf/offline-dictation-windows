# Disclaimer · Отказ от ответственности

[English](#english) · [Русский](#русский)

## English

This page says in plain words what you take on by using this program. It adds
no conditions to the licence and asks you to accept nothing: you can run the
program without agreeing to anything. The binding text is the GNU General
Public License v3 in [LICENSE](LICENSE), sections 15 to 17.

1. **No warranty.** The program is free and comes as is. It may fail, and you
   use it at your own risk.

2. **Text goes where the focus is.** When a dictation finishes, the text is
   typed into the window that is in front at that moment. If that is a chat, a
   terminal or a form, what you said lands there — in a chat it may be sent
   straight away. Check where the cursor is before you speak.

3. **Recognition makes mistakes.** Words get misheard or dropped, punctuation
   and capital letters go astray. The `small` model on a computer without an
   NVIDIA graphics card makes noticeably more of them than `large-v3` on one.
   Read the text before you send it or run it. Do not use it unchecked for
   medical, legal or financial writing, or for commands.

4. **The microphone gate affects every program.** It is off by default. Turned
   on, it closes the microphone for all desktop applications, not just this
   one — voice messages and calls stop working until it is opened again. It
   does not protect against malicious software.

5. **Internet and other companies.** The first run downloads the speech model
   from Hugging Face. After that the program needs no internet. If you turn on
   the OpenAI mode, your recordings are sent to OpenAI and their terms apply.

6. **What stays on your disk.** In the program folder: the settings
   (`src/config.yaml`), the OpenAI API key if you entered one (`.env`, plain
   text), and the logs (`ww_*.log`) — what the program did and what went wrong.
   What you dictate is not written to the logs unless you turn on
   `log_transcribed_text`.

7. **An independent fork.** This is a modified version of
   [savbell/whisper-writer](https://github.com/savbell/whisper-writer). It is
   not affiliated with or endorsed by its author or by OpenAI.

8. **Liability.** Sections 15 and 16 of the licence exclude warranty and
   liability as far as the applicable law allows. Where the law does not allow
   that in full — for intent or gross negligence, for instance — the law
   applies.

## Русский

Здесь простыми словами сказано, что вы берёте на себя, когда пользуетесь
программой. Документ не добавляет к лицензии никаких условий и ничего не просит
принять: запускать программу можно, ни с чем не соглашаясь. Юридически действует
текст GNU General Public License v3 в файле [LICENSE](LICENSE), разделы 15–17.

1. **Без гарантий.** Программа бесплатная и даётся как есть. Она может
   работать с ошибками, вы пользуетесь ей на свой риск.

2. **Текст уходит туда, где курсор.** Когда диктовка закончилась, текст
   печатается в окно, которое в этот момент впереди. Если это чат, командная
   строка или форма, сказанное окажется там, а в чате может сразу уйти
   собеседнику. Перед тем как говорить, посмотрите, где курсор.

3. **Распознавание ошибается.** Слова слышатся неверно или пропадают, путаются
   знаки препинания и заглавные буквы. Модель `small` на компьютере без
   видеокарты NVIDIA ошибается заметно чаще, чем `large-v3` на видеокарте.
   Перечитайте текст, прежде чем отправить или выполнить его. Не используйте
   его без проверки в медицинских, юридических и финансовых текстах и для
   команд.

4. **Замок микрофона действует на все программы.** По умолчанию он выключен.
   Если включить, он закрывает микрофон всем программам на компьютере, а не
   только этой: голосовые сообщения и звонки перестанут работать, пока его не
   откроют. От вредоносных программ он не защищает.

5. **Интернет и другие компании.** При первом запуске модель распознавания
   скачивается с Hugging Face. Дальше интернет не нужен. Если включить режим
   OpenAI, записи уходят в OpenAI, и действуют их условия.

6. **Что остаётся на диске.** В папке программы лежат настройки
   (`src/config.yaml`), ключ OpenAI, если вы его вводили (`.env`, открытым
   текстом), и журналы (`ww_*.log`) — что программа делала и где ошиблась.
   Продиктованный текст в журналы не пишется, пока вы не включите
   `log_transcribed_text`.

7. **Независимый форк.** Это изменённая версия
   [savbell/whisper-writer](https://github.com/savbell/whisper-writer). С её
   автором и с OpenAI проект не связан, они его не одобряли.

8. **Ответственность.** Разделы 15 и 16 лицензии исключают гарантии и
   ответственность в той мере, в какой это позволяет применимое право. Где
   право не позволяет исключить их полностью — например, при умысле или грубой
   неосторожности, — действует закон.
