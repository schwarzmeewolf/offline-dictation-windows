"""
The version of this fork.

Numbering continues from upstream rather than restarting: savbell/whisper-writer
released 1.0.1 and then stopped. This fork carries that release plus the work
that was sitting unreleased there, and changes enough on top - configuration
keys, startup behaviour, the microphone gate - that a major bump is the honest
signal to anyone upgrading.
"""

# An alpha: the settings and the behaviour may still change between releases,
# and the version says so wherever it is shown - log, tray, settings window,
# support file.
__version__ = '2.3.0-alpha.1'

# The upstream release this fork started from, so the lineage stays checkable
# even after the histories have drifted apart.
UPSTREAM_BASE = '1.0.1'
