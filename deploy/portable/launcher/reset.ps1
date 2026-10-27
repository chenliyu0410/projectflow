param([switch]$Yes)
. (Join-Path $PSScriptRoot 'common.ps1')

if (-not $Yes) {
    Say '這會把展示資料還原成剛解壓縮時的樣子。目前的資料會改名保留，不會刪除。'
    if ((Read-Host '確定要還原嗎？輸入 Y 繼續') -notin 'Y', 'y') { Say '已取消。'; return }
}
[void](Stop-Package)
if (@(Get-PackageProcesses).Count) { Fail '有程式沒有停下來，請重新開機後再試。' }
if (Test-Path -LiteralPath $DataDir) {
    $backup = Join-Path $Root ('data-備份-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
    Move-Item -LiteralPath $DataDir -Destination $backup
    Say "原本的資料已改名為 $(Split-Path $backup -Leaf)"
}
Copy-Seed
Say '已還原成乾淨的展示資料。請執行「啟動專流.bat」。'
