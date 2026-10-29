"""
Language names for the settings window.

People recognise their language by its name, not by an ISO code: the settings
used to ask for 'ru' in an empty text field, and an empty field meant
"auto-detect" without saying so. Each language is listed under its own name,
so the list reads the same whatever the interface language.

Whisper understands about a hundred languages. This is the shorter list a
person would look through; a code set by hand that is not on it is kept and
shown as the code.
"""

# (code, name). None is auto-detect, whose name the interface translates.
DICTATION_LANGUAGES = (
    (None, 'Auto-detect'),
    ('en', 'English'),
    ('ru', 'Русский'),
    ('uk', 'Українська'),
    ('be', 'Беларуская'),
    ('kk', 'Қазақ тілі'),
    ('de', 'Deutsch'),
    ('fr', 'Français'),
    ('es', 'Español'),
    ('it', 'Italiano'),
    ('pt', 'Português'),
    ('nl', 'Nederlands'),
    ('pl', 'Polski'),
    ('cs', 'Čeština'),
    ('sq', 'Shqip'),
    ('sr', 'Српски'),
    ('bg', 'Български'),
    ('el', 'Ελληνικά'),
    ('tr', 'Türkçe'),
    ('sv', 'Svenska'),
    ('fi', 'Suomi'),
    ('ka', 'ქართული'),
    ('hy', 'Հայերեն'),
    ('he', 'עברית'),
    ('ar', 'العربية'),
    ('zh', '中文'),
    ('ja', '日本語'),
    ('ko', '한국어'),
)

# The interface itself speaks these two.
UI_LANGUAGES = (('en', 'English'), ('ru', 'Русский'))
