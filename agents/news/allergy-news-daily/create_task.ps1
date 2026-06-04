$action = New-ScheduledTaskAction -Execute "D:\D_CC_vscode\agents\news\allergy-news-daily\run_allergy_daily.bat" -WorkingDirectory "D:\D_CC_vscode\agents\news\allergy-news-daily"
$trigger = New-ScheduledTaskTrigger -Daily -At "08:00AM"
Register-ScheduledTask -TaskName "AllergyDailyReport" -Action $action -Trigger $trigger -Force
Write-Host "Task created successfully."
