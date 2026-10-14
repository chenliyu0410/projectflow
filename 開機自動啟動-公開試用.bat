@echo off
rem ProjectFlow - publish the trial on the internet through Tailscale Funnel at logon.
rem
rem Put a SHORTCUT to this file in the Startup folder (Win+R -> shell:startup).
rem Do not copy the file there: it finds the repo through its own folder.
rem
rem Every message comes from deploy\public_trial.py. This file stays ASCII-only and
rem CRLF (pinned in .gitattributes) because cmd.exe parses batch files in the
rem console code page (950 here), where UTF-8 Chinese text breaks the parser.
rem
rem Docker keeps ProjectFlow running after this window closes. Run the stop
rem script next to this file to take the public URL down.
setlocal
cd /d "%~dp0"
title ProjectFlow - public trial
chcp 65001 >nul

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] python was not found on PATH. Install Python 3.13, then run this again.
  pause
  exit /b 1
)

python deploy\public_trial.py
pause
