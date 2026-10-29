@echo off
title Run Test Suite - Multimodal Agent
echo ======================================================================
echo  MULTIMODAL ATTENDANCE & ENGAGEMENT AGENT - TEST SUITE
echo ======================================================================
echo.

where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set PYTHON_CMD=py
) else (
    set PYTHON_CMD=python
)

echo [*] Executing pytest unit and integration test suite...
%PYTHON_CMD% -m pytest tests/ -v

echo.
echo [*] Tests complete.
pause
