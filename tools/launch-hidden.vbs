' Start the dictation launcher without a console window.
'
' start-dictation.bat is a console program, so starting it from a shortcut
' flashes a black window up for a moment. Run through wscript with window
' style 0, it starts hidden. The paths come from this file's own location,
' so the project can live in any folder, including one with spaces.

Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(fso.GetParentFolderName(WScript.ScriptFullName))
CreateObject("WScript.Shell").Run """" & root & "\start-dictation.bat""", 0, False
