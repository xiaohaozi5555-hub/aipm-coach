param(
    [string]$OutputDir = "coach-data\screenshots",
    [string]$Prefix = "screenshot"
)

$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

if (-not [System.Windows.Forms.Clipboard]::ContainsImage()) {
    Write-Host "FAIL: Clipboard does not contain an image."
    Write-Host "Use capture_screen.ps1 first, or copy an image to the clipboard."
    exit 1
}

$dir = New-Item -ItemType Directory -Force -Path $OutputDir
$timestamp = Get-Date -Format "yyyy-MM-dd-HH-mm-ss"
$fileName = "$Prefix-$timestamp.png"
$path = Join-Path $dir.FullName $fileName

$image = [System.Windows.Forms.Clipboard]::GetImage()
$image.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
$image.Dispose()

Write-Host "OK: Saved clipboard image to $path"
