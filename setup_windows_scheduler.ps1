# PowerShell script to set up Windows Task Scheduler for S&P 500 Worker
# Run this script as Administrator

param(
    [string]$ProjectPath = "C:\Users\Deniz\PycharmProjects\MarketInsight",
    [string]$TaskName = "SP500_Metrics_Worker"
)

Write-Host "Setting up Windows Task Scheduler for S&P 500 Worker..." -ForegroundColor Green

# Check if running as Administrator
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "This script requires Administrator privileges. Please run as Administrator." -ForegroundColor Red
    exit 1
}

try {
    # Define the batch file path
    $BatchFile = Join-Path $ProjectPath "run_sp500_worker.bat"

    if (-not (Test-Path $BatchFile)) {
        Write-Host "Batch file not found at: $BatchFile" -ForegroundColor Red
        Write-Host "Please ensure the run_sp500_worker.bat file exists in your project directory." -ForegroundColor Red
        exit 1
    }

    # Create the scheduled task action
    $Action = New-ScheduledTaskAction -Execute $BatchFile -WorkingDirectory $ProjectPath

    # Create the trigger to run every minute
    $Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 1) -RepetitionDuration (New-TimeSpan -Days 365)

    # Create task settings
    $Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RunOnlyIfNetworkAvailable

    # Create the principal (run as current user)
    $Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType InteractiveOrPassword

    # Remove existing task if it exists
    try {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
        Write-Host "Removed existing task: $TaskName" -ForegroundColor Yellow
    } catch {
        # Task doesn't exist, continue
    }

    # Create and register the scheduled task
    $Task = New-ScheduledTask -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Description "S&P 500 Metrics Worker - Fetches company data every minute"

    Register-ScheduledTask -TaskName $TaskName -InputObject $Task

    Write-Host "Successfully created scheduled task: $TaskName" -ForegroundColor Green
    Write-Host "The task will run every minute to fetch S&P 500 company metrics." -ForegroundColor Green
    Write-Host ""
    Write-Host "To manage the task:" -ForegroundColor Cyan
    Write-Host "  - Open Task Scheduler (taskschd.msc)" -ForegroundColor White
    Write-Host "  - Navigate to Task Scheduler Library" -ForegroundColor White
    Write-Host "  - Find task: $TaskName" -ForegroundColor White
    Write-Host ""
    Write-Host "To view logs:" -ForegroundColor Cyan
    Write-Host "  - Check: $ProjectPath\logs\sp500_worker.log" -ForegroundColor White
    Write-Host ""
    Write-Host "To remove the task:" -ForegroundColor Cyan
    Write-Host "  Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false" -ForegroundColor White

} catch {
    Write-Host "Error setting up scheduled task: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Setup complete! The worker will start running every minute." -ForegroundColor Green