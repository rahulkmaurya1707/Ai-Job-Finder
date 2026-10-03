$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument '-ExecutionPolicy Bypass -File "C:\Users\mrmau\OneDrive\Desktop\job-finder\scheduler\run_pipeline.ps1"' -WorkingDirectory "C:\Users\mrmau\OneDrive\Desktop\job-finder"
$trigger = New-ScheduledTaskTrigger -Daily -At 09:00AM
Register-ScheduledTask -TaskName "Job Finder Daily Run" -Action $action -Trigger $trigger -Force
