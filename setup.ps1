# Finish install / update the code-assist skill (Windows PowerShell).
# First time:  git clone https://github.com/arifbiswas/code-assist.git "$HOME\.claude\skills\code-assist"
#              powershell -ExecutionPolicy Bypass -File "$HOME\.claude\skills\code-assist\setup.ps1"
# Update:      powershell -ExecutionPolicy Bypass -File "$HOME\.claude\skills\code-assist\setup.ps1"
$ErrorActionPreference = "Stop"
$Repo   = "https://github.com/arifbiswas/code-assist.git"
$Skills = Join-Path $HOME ".claude\skills"
$Dest   = Join-Path $Skills "code-assist"
$BkDir  = Join-Path $HOME ".claude\code-assist\backup"
$Stamp  = Get-Date -Format "yyyyMMddHHmmss"

if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw "git is required: https://git-scm.com" }
if (-not ((Get-Command python -ErrorAction SilentlyContinue) -or (Get-Command py -ErrorAction SilentlyContinue))) {
    throw "Python 3.8+ is required: https://www.python.org/downloads/ (tick 'Add to PATH')"
}

$Old = Join-Path $Skills "token-saver"
if (Test-Path $Old) {
    New-Item -ItemType Directory -Force $BkDir | Out-Null
    Move-Item $Old (Join-Path $BkDir "token-saver-$Stamp")
    Write-Host "   old token-saver skill moved to $BkDir"
}

if (Test-Path (Join-Path $Dest ".git")) {
    Write-Host "Updating code-assist..."
    git -C $Dest pull --ff-only --quiet
} else {
    if (Test-Path $Dest) {
        New-Item -ItemType Directory -Force $BkDir | Out-Null
        Move-Item $Dest (Join-Path $BkDir "code-assist-$Stamp")
    }
    New-Item -ItemType Directory -Force $Skills | Out-Null
    git clone --depth 1 --quiet $Repo $Dest
}

Write-Host "code-assist skill ready at $Dest"
Write-Host ""
Write-Host "Next, in any project:"
Write-Host "  - In Claude Code:  /code-assist init"
Write-Host "  - or PowerShell:   powershell -ExecutionPolicy Bypass -File `"$Dest\install.ps1`" -Project C:\path\to\project"
