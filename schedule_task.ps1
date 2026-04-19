# jauction daily auto update - Windows Task Scheduler
# Run as Administrator

$TaskName = "jauction_daily_update"
$ScriptPath = "D:\jauction\update_daily.bat"

Write-Host "============================================================"
Write-Host "  jauction daily update task scheduler register"
Write-Host "============================================================"

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "  Existing task deleted"
}

$Action = New-ScheduledTaskAction -Execute $ScriptPath -WorkingDirectory "D:\jauction"
$Trigger = New-ScheduledTaskTrigger -Daily -At "06:00AM"
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2)

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "jauction daily update"

Write-Host ""
Write-Host "  Done!"
Write-Host "  Task: $TaskName"
Write-Host "  Time: Daily 06:00AM"
Write-Host "  Script: $ScriptPath"
Write-Host "============================================================"