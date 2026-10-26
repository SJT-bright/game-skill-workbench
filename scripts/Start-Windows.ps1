$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$activeFile = Join-Path $env:APPDATA 'GameDesk-Skill-Personal\active-app.json'
if(Test-Path -LiteralPath $activeFile){
    $active = Get-Content -LiteralPath $activeFile -Raw | ConvertFrom-Json
    if($active.exe -and (Test-Path -LiteralPath $active.exe)){ Start-Process -FilePath $active.exe; exit 0 }
}
$runtimeVersion = '43.4.1'
$runtimeRoot = Join-Path $env:LOCALAPPDATA 'GameDesk-Skill-Runtime'
$runtimeDir = Join-Path $runtimeRoot $runtimeVersion
$exe = Join-Path $runtimeDir 'electron.exe'
$archiveName = "electron-v$runtimeVersion-win32-x64.zip"
$hashes = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'electron-43.4.1-checksums.json') -Raw | ConvertFrom-Json
$expected = $hashes.$archiveName
if (-not (Test-Path -LiteralPath $exe)) {
    New-Item -ItemType Directory -Path $runtimeRoot -Force | Out-Null
    $archive = Join-Path $runtimeRoot $archiveName
    $uri = "https://github.com/electron/electron/releases/download/v$runtimeVersion/$archiveName"
    Write-Host 'First launch: downloading desktop runtime. This is needed only once.'
    Invoke-WebRequest -Uri $uri -OutFile $archive -UseBasicParsing
    if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) {
        Remove-Item -LiteralPath $archive -Force
        throw 'Runtime checksum failed. No app was launched.'
    }
    $stage = Join-Path $runtimeRoot ('extract-' + [Guid]::NewGuid().ToString())
    Expand-Archive -LiteralPath $archive -DestinationPath $stage
    if (Test-Path -LiteralPath $runtimeDir) { Remove-Item -LiteralPath $runtimeDir -Recurse -Force }
    Move-Item -LiteralPath $stage -Destination $runtimeDir
    Remove-Item -LiteralPath $archive -Force
}
$appRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
Start-Process -FilePath $exe -ArgumentList ('"' + $appRoot + '"') -WorkingDirectory $appRoot
