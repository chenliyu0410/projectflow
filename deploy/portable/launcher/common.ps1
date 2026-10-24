# Shared by start/stop/reset. Saved as UTF-8 with BOM so Windows PowerShell 5.1 reads the Chinese text.
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$WebPort = 15190
$ModelPort = 11437
$DataDir = Join-Path $Root 'data'
$SeedDir = Join-Path $Root 'seed'
$LogDir = Join-Path $Root 'logs'
$PidFile = Join-Path $DataDir 'pids.json'

function Say([string]$Text) { Write-Host $Text }

function Fail([string]$Text) {
    Write-Host ''
    Write-Host "無法完成：$Text" -ForegroundColor Red
    Write-Host "記錄檔在 $LogDir ，需要協助時請把整個 logs 資料夾傳給提供者。"
    throw $Text
}

# Every process this package starts runs an executable inside the package folder, so ownership is decided
# by path: other Python or Ollama on this computer are never touched.
function Get-PackageProcesses {
    $prefix = $Root.TrimEnd('\') + '\'
    Get-CimInstance Win32_Process | Where-Object {
        $_.ExecutablePath -and $_.ExecutablePath.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)
    }
}

function Stop-Package {
    $running = @(Get-PackageProcesses)
    foreach ($process in $running) {
        try { Stop-Process -Id $process.ProcessId -Force -ErrorAction Stop } catch {}
    }
    for ($i = 0; $i -lt 20 -and @(Get-PackageProcesses).Count; $i++) { Start-Sleep -Milliseconds 250 }
    if (Test-Path -LiteralPath $PidFile) { Remove-Item -LiteralPath $PidFile -Force }
    return $running.Count
}

function Test-PortOwner([int]$Port) {
    $listen = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $listen) { return 'free' }
    $owner = Get-CimInstance Win32_Process -Filter "ProcessId=$($listen.OwningProcess)" -ErrorAction SilentlyContinue
    $prefix = $Root.TrimEnd('\') + '\'
    if ($owner -and $owner.ExecutablePath -and $owner.ExecutablePath.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) { return 'ours' }
    return 'other'
}

function Copy-Seed {
    if (-not (Test-Path -LiteralPath (Join-Path $SeedDir 'projectflow.sqlite'))) { Fail '找不到 seed 資料夾裡的展示資料，壓縮檔可能沒有完整解開。' }
    Copy-Item -LiteralPath $SeedDir -Destination $DataDir -Recurse
    Remove-Item -LiteralPath (Join-Path $DataDir 'seed.json') -Force -ErrorAction SilentlyContinue
}
