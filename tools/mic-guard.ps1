<#
.SYNOPSIS
    Открыть, закрыть и проверить доступ приложений к микрофону.

.DESCRIPTION
    Работает через CapabilityAccessManager в HKCU - тот же переключатель, что
    сидит в Параметрах -> Конфиденциальность -> Микрофон. Прав администратора
    не требует. Это настоящая граница для обычных приложений: брокер
    возможностей отказывает им в захвате. Но код, запущенный от вашего имени,
    вернёт разрешение так же легко, как этот скрипт, - гарантию даёт только
    аппаратная кнопка на корпусе микрофона.

    Флаг mute на устройстве снимается и ставится через mic_gate.py, если рядом
    найден venv проекта. Это удобство, а не защита: mute снимает любой процесс.

.EXAMPLE
    .\mic-guard.ps1 -Status
    .\mic-guard.ps1 -Close
    .\mic-guard.ps1 -Open
    .\mic-guard.ps1 -Audit
#>
[CmdletBinding(DefaultParameterSetName = 'Status')]
param(
    [Parameter(ParameterSetName='Status')][switch]$Status,
    [Parameter(ParameterSetName='Open')]  [switch]$Open,
    [Parameter(ParameterSetName='Close')] [switch]$Close,
    [Parameter(ParameterSetName='Audit')] [switch]$Audit
)

$ErrorActionPreference = 'Stop'
$Consent = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone'
$Root    = Split-Path -Parent $PSScriptRoot

function Set-Consent([string]$Value) {
    foreach ($k in @($Consent, "$Consent\NonPackaged")) {
        if (Test-Path $k) { Set-ItemProperty -Path $k -Name Value -Value $Value }
    }
}

function Set-EndpointMute([bool]$Flag) {
    # Лучшее усилие: без venv проекта просто пропускаем, consent важнее.
    $py = Join-Path $Root 'venv\Scripts\python.exe'
    if (-not (Test-Path $py)) { return }
    $arg = if ($Flag) { 'True' } else { 'False' }
    $code = "import sys; sys.path.insert(0,r'$Root\src'); " +
            "from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume; " +
            "from ctypes import cast, POINTER; from comtypes import CLSCTX_ALL; " +
            "import comtypes; comtypes.CoInitialize(); " +
            "m=AudioUtilities.GetMicrophone(); " +
            "cast(m.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None), POINTER(IAudioEndpointVolume)).SetMute($arg, None)"
    try { & $py -c $code 2>$null | Out-Null } catch { }
}

function Get-MicState {
    $v = (Get-ItemProperty $Consent -ErrorAction SilentlyContinue).Value
    $py = Join-Path $Root 'venv\Scripts\python.exe'
    $mute = '?'
    if (Test-Path $py) {
        $code = "from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume; " +
                "from ctypes import cast, POINTER; from comtypes import CLSCTX_ALL; " +
                "import comtypes; comtypes.CoInitialize(); " +
                "m=AudioUtilities.GetMicrophone(); " +
                "print(cast(m.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None), POINTER(IAudioEndpointVolume)).GetMute())"
        try { $mute = (& $py -c $code 2>$null | Select-Object -Last 1) } catch { }
    }
    [PSCustomObject]@{ Consent = $v; Muted = $mute }
}

function Get-MicUsers {
    $np = "$Consent\NonPackaged"
    if (-not (Test-Path $np)) { return @() }
    Get-ChildItem $np | ForEach-Object {
        $p = Get-ItemProperty $_.PSPath
        if ($null -eq $p.LastUsedTimeStart) { return }
        $active = ($p.LastUsedTimeStop -eq 0)
        $when = if ($active) { Get-Date } else { [datetime]::FromFileTime($p.LastUsedTimeStop) }
        [PSCustomObject]@{
            Active = $active
            Last   = $when
            App    = ($_.PSChildName -replace '#', '\')
        }
    } | Sort-Object Last -Descending
}

switch ($PSCmdlet.ParameterSetName) {
    'Open' {
        Set-Consent 'Allow'; Set-EndpointMute $false
        $s = Get-MicState
        Write-Output "МИКРОФОН ОТКРЫТ   consent=$($s.Consent)  muted=$($s.Muted)"
    }
    'Close' {
        Set-Consent 'Deny'; Set-EndpointMute $true
        $s = Get-MicState
        Write-Output "МИКРОФОН ЗАКРЫТ   consent=$($s.Consent)  muted=$($s.Muted)"
    }
    'Audit' {
        $s = Get-MicState
        Write-Output "Состояние: consent=$($s.Consent)  muted=$($s.Muted)"
        Write-Output ''
        $users = Get-MicUsers
        $now = $users | Where-Object Active
        if ($now) {
            Write-Output 'СЕЙЧАС ДЕРЖАТ МИКРОФОН:'
            $now | ForEach-Object { Write-Output "   $($_.App)" }
        } else {
            Write-Output 'Сейчас микрофон никто не держит.'
        }
        Write-Output ''
        Write-Output 'Последние обращения:'
        $users | Where-Object { -not $_.Active } | Select-Object -First 20 |
            ForEach-Object { Write-Output ("   {0:yyyy-MM-dd HH:mm}  {1}" -f $_.Last, $_.App) }
    }
    default {
        $s = Get-MicState
        $verdict = if ($s.Consent -eq 'Deny') { 'ЗАКРЫТ' } else { 'ОТКРЫТ' }
        Write-Output "Микрофон: $verdict   consent=$($s.Consent)  muted=$($s.Muted)"
        $now = Get-MicUsers | Where-Object Active
        if ($now) { $now | ForEach-Object { Write-Output "   держит: $($_.App)" } }
    }
}
