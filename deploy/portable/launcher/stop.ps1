. (Join-Path $PSScriptRoot 'common.ps1')

$count = Stop-Package
if (@(Get-PackageProcesses).Count) { Fail '有程式沒有停下來，請重新開機後再試。' }
if ($count) { Say "專流已停止（結束 $count 個程式）。" } else { Say '專流沒有在執行。' }
