@echo off
setlocal
title Nanfeng Downloader - YouTube Compatibility Setup

set "PROJECT_ROOT=%~dp0"
set "RUNTIME_ROOT=%LOCALAPPDATA%\NanzhufengVideoDownloader"
set "PROVIDER_ROOT=%RUNTIME_ROOT%\bgutil-ytdlp-pot-provider"
set "SERVER_ROOT=%PROVIDER_ROOT%\server"
if /i "%~1"=="--non-interactive" set "NO_PAUSE=1"

echo Installing yt-dlp, EJS, and the guest PO Token Provider...
echo.

where node >nul 2>&1
if errorlevel 1 (
    echo Node.js 20 or later was not found.
    echo Install Node.js LTS, then run this script again.
    if not defined NO_PAUSE pause
    exit /b 1
)

python -m pip install --upgrade -r "%PROJECT_ROOT%requirements.txt"
if errorlevel 1 (
    echo Python dependency installation failed.
    if not defined NO_PAUSE pause
    exit /b 1
)

if not exist "%PROVIDER_ROOT%\.git" (
    echo Preparing the local PO Token Provider...
    git clone --depth 1 --branch 1.3.1 https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git "%PROVIDER_ROOT%"
    if errorlevel 1 (
        echo Provider download failed. Check network access and Git installation.
        if not defined NO_PAUSE pause
        exit /b 1
    )
)

pushd "%SERVER_ROOT%"
call npm ci
if errorlevel 1 (
    popd
    echo Provider dependency installation failed.
    if not defined NO_PAUSE pause
    exit /b 1
)
call npx tsc
if errorlevel 1 (
    popd
    echo Provider build failed.
    if not defined NO_PAUSE pause
    exit /b 1
)
popd

if not exist "%SERVER_ROOT%\build\generate_once.js" (
    echo Provider build output is missing.
    if not defined NO_PAUSE pause
    exit /b 1
)

echo.
echo Setup complete. Public YouTube content will prefer no-login compatibility.
echo A network exit that YouTube has flagged may still require a different network or proxy node.
if not defined NO_PAUSE pause
