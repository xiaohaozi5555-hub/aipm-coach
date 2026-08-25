param(
    [switch]$SaveAfterCapture,
    [string]$OutputDir = "coach-data\screenshots"
)

$ErrorActionPreference = "Stop"

Write-Host "Starting Windows screen snip..."
Write-Host "Select an area with the snipping overlay. The image will be copied to the clipboard."

Start-Process "ms-screenclip:"

if ($SaveAfterCapture) {
    Write-Host "Waiting 8 seconds for screenshot selection..."
    Start-Sleep -Seconds 8
    $saveScript = Join-Path $PSScriptRoot "save_clipboard_image.ps1"
    powershell -NoProfile -ExecutionPolicy Bypass -STA -File $saveScript -OutputDir $OutputDir
}
else {
    Write-Host "After selecting the area, paste the screenshot into Codex chat with Ctrl+V."
    Write-Host "To save it to a file after capture, run:"
    Write-Host "powershell -NoProfile -ExecutionPolicy Bypass -STA -File plugins\aipm-coach\scripts\save_clipboard_image.ps1"
}
