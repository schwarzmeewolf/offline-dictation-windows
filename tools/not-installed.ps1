# Printed by the launchers when there is no venv yet - that is, when someone
# double-clicked start-dictation.bat before running install.bat. Lives here
# rather than in the .bat because cmd cannot read a .bat holding non-ASCII
# text: it loses its byte position and runs fragments of lines.
Write-Host ''
Write-Host 'WhisperWriter is not installed yet: there is no venv folder.'
Write-Host 'Run install.bat first (double-click it), then start this again.'
Write-Host ''
Write-Host 'WhisperWriter ещё не установлен: нет папки venv.' -ForegroundColor DarkGray
Write-Host 'Сначала запустите install.bat (двойным щелчком), потом снова этот файл.' -ForegroundColor DarkGray
Write-Host ''