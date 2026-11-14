# code-assist: install into a project (Windows PowerShell)
#   powershell -ExecutionPolicy Bypass -File "$HOME\.claude\skills\code-assist\install.ps1" [-Project C:\path\to\project] [-NoAgents]
param([string]$Project = (Get-Location).Path, [switch]$NoAgents)
$ErrorActionPreference = "Stop"
$Dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Py = $null
foreach ($cand in @("python", "py -3", "python3")) {
    $parts = $cand.Split(" ")
    $rest = @($parts | Select-Object -Skip 1)
    try {
        & $parts[0] @rest -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" 2>$null
        if ($LASTEXITCODE -eq 0) { $Py = $parts; break }
    } catch {}
}
if (-not $Py) { throw "Python 3.8+ is required: https://www.python.org/downloads/ (tick 'Add to PATH')" }
$env:CODE_ASSIST_PY = ($Py -join " ")
$rest = @($Py | Select-Object -Skip 1)
$extra = @()
if ($NoAgents) { $extra += "--no-agents" }
& $Py[0] @rest (Join-Path $Dir "scripts\install.py") $Project @extra
