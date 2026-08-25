[CmdletBinding()]
param(
    [switch]$SkipPythonDependencies
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$marketplaceName = 'aipm-coach-marketplace'
$pluginSelector = "aipm-coach@$marketplaceName"

if (-not (Get-Command codex -ErrorAction SilentlyContinue)) {
    throw 'Codex CLI is not available in PATH. Install or update Codex before installing this plugin.'
}

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw 'Python is not available in PATH. Python 3.11 or newer is recommended.'
}

if (-not $SkipPythonDependencies) {
    & python -m pip install -r (Join-Path $repoRoot 'requirements.txt')
    if ($LASTEXITCODE -ne 0) {
        throw 'Python dependency installation failed.'
    }
}

$marketplaces = (& codex plugin marketplace list 2>&1 | Out-String)
if ($LASTEXITCODE -ne 0) {
    throw 'Unable to read configured Codex plugin marketplaces.'
}

if ($marketplaces -notmatch [regex]::Escape($marketplaceName)) {
    & codex plugin marketplace add $repoRoot
    if ($LASTEXITCODE -ne 0) {
        throw 'Unable to add the local AIPM Coach marketplace.'
    }
}

& codex plugin add $pluginSelector
if ($LASTEXITCODE -ne 0) {
    throw 'Unable to install AIPM Coach from the configured marketplace.'
}

Write-Host ''
Write-Host 'AIPM Coach installed successfully.' -ForegroundColor Green
Write-Host 'Start a new Codex task in this repository and say:'
Write-Host 'AIPM教练：按完整流程处理我的项目问题。'
