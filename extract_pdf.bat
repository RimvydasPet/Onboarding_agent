@echo off
setlocal enabledelayedexpansion

REM Try to find Python installation
for /f "delims=" %%i in ('where python 2^>nul') do set PYTHON=%%i

if not defined PYTHON (
    for /f "delims=" %%i in ('where python3 2^>nul') do set PYTHON=%%i
)

if not defined PYTHON (
    echo Python not found in PATH
    exit /b 1
)

REM Run the extraction script
"%PYTHON%" "%~dp0extract_pdf.py"
