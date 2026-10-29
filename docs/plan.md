# Plan

What is still to be done for the public version, and the decisions that go
with it. Done work goes to CHANGELOG.md, not here.

## Antivirus check (VirusTotal)

Done on the final build, the one that goes to people. Only `WhisperWriter.exe`
and its `_internal` folder are uploaded. An uploaded file stays with the
antivirus companies for good, so until then the only check is a search by
SHA256, which sends the hash and nothing else. If more than two or three
engines flag the build, build PyInstaller's bootloader from source or sign
the exe.

The ready-to-run archive is already on the v2.2.0 release, so this check is
due. Nothing is uploaded without the owner's yes.

The source archive needs no check of its own: `tools/launch-hidden.vbs`, a
hidden start through VBScript and a common cause of heuristic alarms, was
removed in 694542e.
