# Windows system OCR (Windows.Media.Ocr) for chinese_audit.py (English pack, 2026-11-01).
# NOT TRIED ON A WINDOWS MACHINE YET: written and syntax-reviewed on macOS only.
#   powershell -NoProfile -ExecutionPolicy Bypass -File ocr_windows.ps1 -Probe
#       -> {"os": "...", "languages": ["zh-Hans-CN", "en-US", ...]}   (installed OCR languages)
#   powershell -NoProfile -ExecutionPolicy Bypass -File ocr_windows.ps1 -List list.json -Out out.json
#       list.json: [{"id": "...", "path": "..."}]
#       out.json : {"engine": "windows", "results": [{"id", "ok", "error", "items": [{"text", "confidence": null, "box"}]}]}
# Every installed Chinese OCR language and English are run on each picture; lines from all of them are kept.
# Windows OCR gives no confidence, so "confidence" is null. Needs Windows 10/11 with Windows PowerShell 5.1
# (WinRT types); Chinese needs the Chinese language with "Optical character recognition" installed.
param(
    [string]$List = '',
    [string]$Out = '',
    [switch]$Probe
)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType = WindowsRuntime]
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
$null = [Windows.Globalization.Language, Windows.Globalization, ContentType = WindowsRuntime]

$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
        $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
        $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]

function Await($op, [Type]$type) {
    $task = $asTaskGeneric.MakeGenericMethod($type).Invoke($null, @($op))
    $task.Wait(-1) | Out-Null
    return $task.Result
}

$langs = @([Windows.Media.Ocr.OcrEngine]::AvailableRecognizerLanguages | ForEach-Object { $_.LanguageTag })
if ($Probe) {
    $doc = @{ os = [System.Environment]::OSVersion.VersionString; languages = $langs }
    Write-Output ($doc | ConvertTo-Json -Compress)
    exit 0
}
if (-not $List -or -not $Out) {
    [Console]::Error.WriteLine('usage: ocr_windows.ps1 -List <list.json> -Out <out.json> | -Probe')
    exit 2
}

$engines = @()
foreach ($tag in $langs) {
    if ($tag -like 'zh*' -or $tag -like 'en*') {
        $e = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new($tag))
        if ($e) { $engines += $e }
    }
}

$jobs = Get-Content -Raw -Encoding UTF8 -Path $List | ConvertFrom-Json
$results = @()
foreach ($job in $jobs) {
    $row = [ordered]@{ id = $job.id; ok = $false; error = $null; items = @() }
    try {
        if ($engines.Count -eq 0) { throw 'no OCR language installed' }
        $file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($job.path)) ([Windows.Storage.StorageFile])
        $stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
        $decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
        $bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
        $items = @()
        foreach ($engine in $engines) {
            if ($bitmap.PixelWidth -gt [Windows.Media.Ocr.OcrEngine]::MaxImageDimension -or
                $bitmap.PixelHeight -gt [Windows.Media.Ocr.OcrEngine]::MaxImageDimension) {
                throw ('picture larger than OCR limit ' + [Windows.Media.Ocr.OcrEngine]::MaxImageDimension)
            }
            $res = Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
            foreach ($line in $res.Lines) {
                $r = $line.Words | Select-Object -First 1
                $box = $null
                if ($r) { $box = @($r.BoundingRect.X, $r.BoundingRect.Y, $r.BoundingRect.Width, $r.BoundingRect.Height) }
                $items += [ordered]@{ text = $line.Text; confidence = $null; box = $box;
                    language = $engine.RecognizerLanguage.LanguageTag }
            }
        }
        $stream.Dispose()
        $row.items = $items
        $row.ok = $true
    } catch {
        $row.error = [string]$_
    }
    $results += $row
}
$doc = [ordered]@{ engine = 'windows'; results = $results }
$json = $doc | ConvertTo-Json -Depth 8 -Compress
[System.IO.File]::WriteAllText($Out, $json, (New-Object System.Text.UTF8Encoding($false)))
exit 0
