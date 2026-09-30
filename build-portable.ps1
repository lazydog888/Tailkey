$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$pythonPath = Join-Path $PSScriptRoot '.venv-webrtc\Scripts\python.exe'
if (!(Test-Path $pythonPath)) { throw 'Run setup-webrtc.cmd first.' }
& $pythonPath webrtc/export_tailcat_web.py
if ($LASTEXITCODE) { throw 'Browser export failed.' }
& $pythonPath -m PyInstaller --noconfirm Tailkey.spec
if ($LASTEXITCODE) { throw 'Portable build failed.' }
Copy-Item -LiteralPath 'PORTABLE.md' -Destination 'dist\Tailkey\README.md'
New-Item -ItemType Directory -Force -Path 'release' | Out-Null
Compress-Archive -Path 'dist\Tailkey' -DestinationPath 'release\Tailkey-Windows-x64.zip' -Force
Write-Host 'Portable app: release\Tailkey-Windows-x64.zip'
