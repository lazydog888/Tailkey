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
# Unsigned build: publish this checksum with the release so downloads can be verified.
$hash = (Get-FileHash 'release\Tailkey-Windows-x64.zip' -Algorithm SHA256).Hash.ToLower()
Set-Content -LiteralPath 'release\SHA256SUMS.txt' -Value "$hash  Tailkey-Windows-x64.zip" -Encoding ascii
Write-Host 'Portable app: release\Tailkey-Windows-x64.zip'
Write-Host "SHA-256: $hash"
