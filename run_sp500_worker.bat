@echo off
REM S&P 500 Worker Batch Script for Windows
REM This script runs the S&P 500 metrics worker

REM Configuration - Update these paths for your environment
set PROJECT_DIR=C:\Users\Deniz\PycharmProjects\MarketInsight
set PYTHON_EXE=python
set LOG_DIR=%PROJECT_DIR%\logs
set LOG_FILE=%LOG_DIR%\sp500_worker.log

REM Create logs directory if it doesn't exist
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

REM Change to project directory
cd /d "%PROJECT_DIR%"

REM Get current timestamp
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "YY=%dt:~2,2%" & set "YYYY=%dt:~0,4%" & set "MM=%dt:~4,2%" & set "DD=%dt:~6,2%"
set "HH=%dt:~8,2%" & set "Min=%dt:~10,2%" & set "Sec=%dt:~12,2%"
set "timestamp=%YYYY%-%MM%-%DD% %HH%:%Min%:%Sec%"

REM Log the start of the job
echo [%timestamp%] Starting S&P 500 worker... >> "%LOG_FILE%"

REM Run the worker with limited batch size to respect rate limits
REM Process 10 companies per run with 1 second delay between requests
%PYTHON_EXE% manage.py sp500_worker --batch-size=10 --delay=1.0 --max-companies=10 >> "%LOG_FILE%" 2>&1

REM Log completion
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "YY=%dt:~2,2%" & set "YYYY=%dt:~0,4%" & set "MM=%dt:~4,2%" & set "DD=%dt:~6,2%"
set "HH=%dt:~8,2%" & set "Min=%dt:~10,2%" & set "Sec=%dt:~12,2%"
set "timestamp=%YYYY%-%MM%-%DD% %HH%:%Min%:%Sec%"
echo [%timestamp%] S&P 500 worker completed. >> "%LOG_FILE%"
echo. >> "%LOG_FILE%"