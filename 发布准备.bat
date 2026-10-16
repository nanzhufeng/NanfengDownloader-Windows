@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Checking the current source and cloud release plan...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\publish_windows_release.ps1" -Plan
echo.
pause
