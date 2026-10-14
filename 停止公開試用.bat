@echo off
rem ProjectFlow - stop the public trial: turn its Funnel off, then restart on
rem loopback only. Data is kept. ASCII-only and CRLF on purpose; every message
rem comes from deploy\public_trial.py.
setlocal
cd /d "%~dp0"
title ProjectFlow - stop public trial
chcp 65001 >nul

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] python was not found on PATH. Install Python 3.13, then run this again.
  pause
  exit /b 1
)

python deploy\public_trial.py --stop
pause
