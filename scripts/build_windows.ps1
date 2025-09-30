param(
  [switch]$OneFile
)

$ErrorActionPreference = 'Stop'

Write-Host "[1/3] Ensure dependencies installed" -ForegroundColor Cyan
python -m pip install --upgrade pip | Out-Null
pip install -r requirements.txt | Out-Null
pip install pyinstaller | Out-Null

Write-Host "[2/3] Build with PyInstaller" -ForegroundColor Cyan
$args = @('--noconfirm', '--windowed', '--name', 'PhotoWatermark', '--collect-all', 'PySide6', 'app.py')
if ($OneFile) { $args = @('--noconfirm', '--windowed', '--name', 'PhotoWatermark', '--onefile', '--collect-all', 'PySide6', 'app.py') }
pyinstaller @args

Write-Host "[3/3] Package zip" -ForegroundColor Cyan
if (Test-Path dist/PhotoWatermark) {
  Compress-Archive -Path "dist/PhotoWatermark/*" -DestinationPath "PhotoWatermark-win64.zip" -Force
} elseif (Test-Path dist/PhotoWatermark.exe) {
  Compress-Archive -Path "dist/PhotoWatermark.exe" -DestinationPath "PhotoWatermark-win64.zip" -Force
}

Write-Host "Done. Output: PhotoWatermark-win64.zip" -ForegroundColor Green
