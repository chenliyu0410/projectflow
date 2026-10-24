. (Join-Path $PSScriptRoot 'common.ps1')

$Python = Join-Path $Root 'runtime\python\python.exe'
$Ollama = Join-Path $Root 'runtime\ollama\ollama.exe'
$Url = "http://127.0.0.1:$WebPort"
# Automated checks set PF_PORTABLE_NO_BROWSER so a test run does not pop up a browser window.
function Open-Browser { if (-not $env:PF_PORTABLE_NO_BROWSER) { Start-Process $Url } }

Say '專流展示包：啟動中…'

# 1. Computer checks
if (-not [Environment]::Is64BitOperatingSystem -or [Environment]::OSVersion.Version.Major -lt 10) {
    Fail '這台電腦不是 64 位元的 Windows 10／11。'
}
foreach ($required in @($Python, $Ollama, (Join-Path $Root 'app\serve.py'), (Join-Path $Root 'app\web\index.html'))) {
    if (-not (Test-Path -LiteralPath $required)) { Fail "缺少檔案 $required ，壓縮檔可能沒有完整解開。" }
}
$drive = Get-PSDrive -Name ($Root.Substring(0, 1))
if ($drive.Free -lt 5GB) { Fail ("磁碟 {0}: 剩餘空間不足 5GB（目前 {1:N1}GB），請清出空間或把資料夾放到其他磁碟。" -f $drive.Name, ($drive.Free / 1GB)) }
$memory = (Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory
if ($memory -lt 16GB) { Say ("提醒：記憶體 {0:N0}GB，少於 16GB，AI 回答可能較慢。" -f ($memory / 1GB)) }

$web = Test-PortOwner $WebPort
$model = Test-PortOwner $ModelPort
if ($web -eq 'ours' -and $model -eq 'ours') {
    Say "專流已經在執行，直接開啟 $Url"
    Open-Browser
    return
}
if ($web -eq 'other') { Fail "連接埠 $WebPort 被其他程式占用，請先關閉該程式。" }
if ($model -eq 'other') { Fail "連接埠 $ModelPort 被其他程式占用，請先關閉該程式。" }
if ($web -eq 'ours' -or $model -eq 'ours') { [void](Stop-Package) }  # half-started earlier; start over cleanly

$gpu = (Get-CimInstance Win32_VideoController | ForEach-Object { $_.Name }) -join '、'
if ($gpu -match 'NVIDIA|AMD|Radeon') { Say "顯示卡：$gpu，AI 會優先用顯示卡執行。" }
else { Say "顯示卡：$gpu。AI 會用 CPU 執行，一題可能要 30 秒以上。" }

# 2. Data: the first start copies the clean demo data
if (-not (Test-Path -LiteralPath (Join-Path $DataDir 'projectflow.sqlite'))) {
    Say '第一次啟動：準備展示資料…'
    Copy-Seed
}
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
foreach ($name in 'api.log', 'api-error.log', 'ollama.log', 'ollama-error.log') {
    $log = Join-Path $LogDir $name
    if (Test-Path -LiteralPath $log) { Move-Item -LiteralPath $log -Destination "$log.1" -Force }
}

# 3. Start the model service and the web/API server, loopback only, with nothing inherited from this computer
foreach ($name in 'PYTHONPATH', 'PYTHONHOME', 'VIRTUAL_ENV', 'OLLAMA_HOST', 'OLLAMA_MODELS', 'OLLAMA_ORIGINS', 'DATABASE_URL') {
    Remove-Item -Path "Env:$name" -ErrorAction SilentlyContinue
}
$env:OLLAMA_HOST = "127.0.0.1:$ModelPort"
$env:OLLAMA_MODELS = Join-Path $Root 'models\ollama'
$env:OLLAMA_NO_CLOUD = '1'
$env:OLLAMA_NUM_PARALLEL = '1'
$env:OLLAMA_MAX_LOADED_MODELS = '2'   # chat model and bge-m3 stay loaded together
$env:OLLAMA_CONTEXT_LENGTH = '8192'
$env:OLLAMA_NOPRUNE = '1'
$ollamaProcess = Start-Process -FilePath $Ollama -ArgumentList 'serve' -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $LogDir 'ollama.log') -RedirectStandardError (Join-Path $LogDir 'ollama-error.log')

$env:DATABASE_URL = 'sqlite:///' + (Join-Path $DataDir 'projectflow.sqlite').Replace('\', '/')
$env:PF_ATTACHMENT_ROOT = Join-Path $DataDir 'files'
$env:PF_AI_ROOT = Join-Path $DataDir 'ai'
$env:PF_AI_OCR_MODEL_DIR = Join-Path $Root 'models\ocr'
$env:PF_AI_VECTOR_MODEL = 'bge-m3'
$env:PF_ACCEPTANCE_MODE = 'true'
$env:PF_AI_FORMAL_INDEX = 'true'
$env:PF_AI_INDEX_AUTO_UPDATE = 'true'
$env:PF_SHOWCASE_MODE = 'false'
# -E -s: ignore PYTHON* variables and user site-packages from this computer.
$apiProcess = Start-Process -FilePath $Python -ArgumentList '-E', '-s', '-X', 'utf8', 'serve.py', '--port', $WebPort, '--web', 'web' `
    -WorkingDirectory (Join-Path $Root 'app') -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $LogDir 'api.log') -RedirectStandardError (Join-Path $LogDir 'api-error.log')
@{ ollama = $ollamaProcess.Id; api = $apiProcess.Id } | ConvertTo-Json | Set-Content -LiteralPath $PidFile -Encoding UTF8

# 4. Wait until both answer, then open the browser
$ready = $false
for ($i = 0; $i -lt 180; $i++) {
    if ($apiProcess.HasExited) { Fail '網站程式啟動失敗（見 logs\api-error.log）。' }
    if ($ollamaProcess.HasExited) { Fail 'AI 模型服務啟動失敗（見 logs\ollama-error.log）。' }
    try {
        $api = (Invoke-RestMethod "$Url/api/health/acceptance" -TimeoutSec 2).acceptance -eq $true
        $models = (Invoke-RestMethod "http://127.0.0.1:$ModelPort/api/tags" -TimeoutSec 2).models.name
        if ($api -and ($models -contains 'pf-qwen3-rag:latest') -and ($models -contains 'bge-m3:latest')) { $ready = $true; break }
    } catch {}
    Start-Sleep -Milliseconds 500
}
if (-not $ready) { [void](Stop-Package); Fail '90 秒內沒有啟動完成，已停止。' }

Say ''
Say "專流已啟動：$Url"
Say '帳號 yu／密碼 demo-yu（毛研食品管理者）。第一次問 AI 要載入模型，約需 10–30 秒。'
Say '用完請執行「停止專流.bat」。'
Open-Browser
