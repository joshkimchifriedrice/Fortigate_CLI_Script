# Get the profile name
$Profile = Read-Host "Enter the credential profile name to use"

if ([string]::IsNullOrWhiteSpace($Profile)) {
    Write-Host "Error: Profile name cannot be empty." -ForegroundColor Red
    exit
}

# Get the timer intervals
$HoursStr = Read-Host "Enter hours to wait between runs (0-23)"
$MinutesStr = Read-Host "Enter minutes to wait between runs (0-59)"

# Default to 0 if nothing is entered
[int]$Hours = if ([string]::IsNullOrWhiteSpace($HoursStr)) { 0 } else { $HoursStr }
[int]$Minutes = if ([string]::IsNullOrWhiteSpace($MinutesStr)) { 0 } else { $MinutesStr }

if ($Hours -eq 0 -and $Minutes -eq 0) {
    Write-Host "Error: Total interval cannot be 0. Exiting." -ForegroundColor Red
    exit
}

# Setup paths (using current directory)
$WorkDir = (Get-Location).Path
$PythonExe = Join-Path -Path $WorkDir -ChildPath ".venv\Scripts\python.exe"
$TaskName = "fortigate_tool_${Profile}_Timer"

# Create the scheduled task action
$Action = if (Test-Path -Path $PythonExe) {
    New-ScheduledTaskAction -Execute $PythonExe -Argument "`"fortigate_tool.py`" run $Profile darrp" -WorkingDirectory $WorkDir
} else {
    Write-Host "Warning: Virtual environment not found. Using system Python." -ForegroundColor Yellow
    New-ScheduledTaskAction -Execute "py.exe" -Argument "`"fortigate_tool.py`" run $Profile darrp" -WorkingDirectory $WorkDir
}

# Setup the trigger
$Interval = New-TimeSpan -Hours $Hours -Minutes $Minutes
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval $Interval
$Trigger.Repetition.Duration = "P3650D"

# Setup settings and register task
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -Hidden
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -User $env:USERNAME -Force

Write-Host "---------------------------------------------------" -ForegroundColor Green
Write-Host "Success! Windows Scheduled Task installed." -ForegroundColor Green
Write-Host "Profile: $Profile" -ForegroundColor Green
Write-Host "Your script will run every $Hours hours and $Minutes minutes." -ForegroundColor Green
Write-Host "Open 'Task Scheduler' and search for '$TaskName' to manage it." -ForegroundColor Green
Write-Host "---------------------------------------------------" -ForegroundColor Green