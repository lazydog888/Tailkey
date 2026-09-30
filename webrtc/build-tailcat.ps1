$ErrorActionPreference = 'Stop'
$tailkeyRoot = Split-Path $PSScriptRoot -Parent
$sourceRoot = Join-Path $tailkeyRoot 'tools\tailcat-src'
$pinnedRevision = 'b4dc28e8aa8936f0a90a41ad8293a64e3d6b645f'
$sdkGo = Join-Path $tailkeyRoot 'tools\go-sdk\go\bin\go.exe'
if (-not (Test-Path -LiteralPath $sdkGo)) {
    $sdkGo = (Get-Command go -ErrorAction Stop).Source
}
if (-not (Test-Path -LiteralPath $sourceRoot)) {
    git clone https://github.com/tailscale/tailcat.git $sourceRoot
    if ($LASTEXITCODE) { throw 'Could not fetch official tailcat source.' }
    git -C $sourceRoot checkout $pinnedRevision
    if ($LASTEXITCODE) { throw 'Could not select pinned revision.' }
}
$actualRevision = git -c "safe.directory=$sourceRoot" -C $sourceRoot rev-parse HEAD
if ($actualRevision -ne $pinnedRevision) { throw 'Tailcat source revision differs from the reviewed build; select the pinned revision first.' }
$oldPath = $env:PATH
$oldCache = $env:GOCACHE
$oldModules = $env:GOMODCACHE
$oldFlags = $env:GOFLAGS
$oldCGO = $env:CGO_ENABLED
try {
    $env:PATH = (Split-Path $sdkGo -Parent) + ';' + $env:PATH
    $env:GOCACHE = Join-Path $tailkeyRoot 'tools\go-build-cache'
    $env:GOMODCACHE = Join-Path $tailkeyRoot 'tools\go-mod-cache'
    $env:GOFLAGS = '-buildvcs=false -trimpath'
    $env:CGO_ENABLED = '0'
    Push-Location (Join-Path $PSScriptRoot 'tailcat-helper')
    try {
        & $sdkGo build -mod=mod -ldflags='-s -w' -o (Join-Path $tailkeyRoot 'tools\tailkey-tailcat.exe') .
        if ($LASTEXITCODE) { throw 'Native tailcat build failed.' }
    } finally { Pop-Location }
    Push-Location $sourceRoot
    try {
        & $sdkGo run ./cmd/tailcat-webdist -o (Join-Path $tailkeyRoot 'tools\tailcat-web')
        if ($LASTEXITCODE) { throw 'Browser tailcat build failed.' }
    } finally { Pop-Location }
    & (Join-Path $tailkeyRoot '.venv-webrtc\Scripts\python.exe') (Join-Path $PSScriptRoot 'export_tailcat_web.py')
    if ($LASTEXITCODE) { throw 'Static browser export failed.' }
} finally {
    $env:PATH = $oldPath
    $env:GOCACHE = $oldCache
    $env:GOMODCACHE = $oldModules
    $env:GOFLAGS = $oldFlags
    $env:CGO_ENABLED = $oldCGO
}
