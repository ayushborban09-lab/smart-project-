@echo off
title Multimodal Attendance & Engagement Agent
echo ======================================================================
echo  MULTIMODAL ATTENDANCE & ENGAGEMENT AGENT
echo  Local Privacy-Preserving Computer Vision & Audio Analytics System
echo ======================================================================
echo.

REM Check Python availability
where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set PYTHON_CMD=py
) else (
    where python >nul 2>nul
    if %ERRORLEVEL% equ 0 (
        set PYTHON_CMD=python
    ) else (
        echo [ERROR] Python not found in PATH. Please install Python 3.10+.
        pause
        exit /b 1
    )
)

echo [*] Starting Multimodal Attendance & Engagement Agent on http://127.0.0.1:5000 ...
echo [*] Processing is local, offline, and privacy-preserving.
echo.

REM Automatically open browser after 2 seconds in parallel
start "" cmd /c "timeout /t 2 >nul & start http://127.0.0.1:5000"

REM Run Flask Server
%PYTHON_CMD% app.py

pause
