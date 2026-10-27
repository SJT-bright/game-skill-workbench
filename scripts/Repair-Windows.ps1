param([string]$InstallDirectory='', [switch]$NoLaunch)
$ErrorActionPreference='Stop'
try {
 if(-not $InstallDirectory){
  Add-Type -AssemblyName System.Windows.Forms
  $pick=New-Object System.Windows.Forms.FolderBrowserDialog
  $pick.Description='Choose the existing game workbench folder containing GameDeskSkill.exe'
  if($pick.ShowDialog() -ne 'OK'){exit 0}
  $InstallDirectory=$pick.SelectedPath
 }
 $target=[IO.Path]::GetFullPath($InstallDirectory)
 $exe=Join-Path $target 'GameDeskSkill.exe'
 $app=Join-Path $target 'resources/app'
 if(-not(Test-Path -LiteralPath $exe) -or -not(Test-Path -LiteralPath (Join-Path $app 'package.json'))){throw 'Select the original installation folder containing GameDeskSkill.exe, not this repair folder.'}
 $old=Get-Content -LiteralPath (Join-Path $app 'package.json') -Raw | ConvertFrom-Json
 if($old.name -ne 'skill-game-dock'){throw 'This folder is not the game workbench.'}
 $busy=Get-Process -Name GameDeskSkill -ErrorAction SilentlyContinue | Where-Object {$_.Path -eq $exe}
 if($busy){throw 'Please exit the workbench from Settings > Exit, then run this repair again. Closing the floating window is not enough.'}
 $payload=Join-Path $PSScriptRoot 'payload'
 $manifest=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'repair-manifest.json') -Raw | ConvertFrom-Json
 $package=Get-Content -LiteralPath (Join-Path $payload 'package.json') -Raw | ConvertFrom-Json
 if($package.name -ne 'skill-game-dock' -or $package.version -ne $manifest.version){throw 'Repair package identity mismatch.'}
 foreach($file in $manifest.files){
  if($file.path -match '(^/|\\|:|(^|/)\.\.(/|$))'){throw 'Invalid repair path.'}
  $p=Join-Path $payload $file.path
  if((Get-Item -LiteralPath $p).Length -ne $file.bytes -or (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant() -ne $file.sha256){throw ('Repair file verification failed: '+$file.path)}
 }
 $incoming=$app+'.repair-'+[guid]::NewGuid().ToString('N')
 $backup=$app+'.before-repair-'+[guid]::NewGuid().ToString('N')
 Copy-Item -LiteralPath $payload -Destination $incoming -Recurse
 foreach($file in $manifest.files){
  $p=Join-Path $incoming $file.path
  if((Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant() -ne $file.sha256){throw 'Copied repair file verification failed.'}
 }
 Move-Item -LiteralPath $app -Destination $backup
 try {Move-Item -LiteralPath $incoming -Destination $app}
 catch {Move-Item -LiteralPath $backup -Destination $app;throw}
 # Keep one recoverable application-file backup; personal data is outside this folder.
 $receipt=@{version=$package.version;previousVersion=$old.version;backup=$backup;updatedAt=[DateTime]::UtcNow.ToString('o')}
 [IO.File]::WriteAllText((Join-Path $target 'repair-receipt.json'),($receipt|ConvertTo-Json),[Text.UTF8Encoding]::new($false))
 Write-Host ('Workbench updated to '+$package.version+'. Your games, chats and personal settings were preserved.')
 if(-not $NoLaunch){Start-Process -FilePath $exe}
} catch {
 Write-Host ('Repair did not complete: '+$_.Exception.Message) -ForegroundColor Red
 if(-not $NoLaunch){Read-Host 'Press Enter to close'}
 exit 1
}
