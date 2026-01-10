@echo off
setlocal enabledelayedexpansion

if "%PROCESSOR_ARCHITECTURE%" == "AMD64" (
    echo [+] 64-bit operating system detected.
    set PYTHON_PATH=.\bin\python3.14.2amd64\python.exe
) else if "%PROCESSOR_ARCHITECTURE%" == "x86" (
    echo [+] 32-bit operating system detected.
    set PYTHON_PATH=.\bin\python3.14.2win32\python.exe
) else (
    echo [-] Unsupported architecture: %PROCESSOR_ARCHITECTURE%
    echo [-] This application only supports [x86] 32-bit or [AMD64] 64-bit systems.
    set /p dummy=Press any key to exit...
    exit 1
)

if not exist "%PYTHON_PATH%" (
    echo [-] Missing embeddedPython executable at: %PYTHON_PATH%
    echo [-] Please ensure the embedded Python is in the correct directory.
    set /p dummy=Press any key to exit...
    exit 1
)

echo [+] Using Python at: %PYTHON_PATH%
@REM echo [+] Checking dependencies...
@REM %PYTHON_PATH% -m pip install -r ./bin/requirements.txt
@REM echo [+] Dependencies installed.
cls

echo [+] Starting application...
cd /d "%~dp0"
%PYTHON_PATH% launcher.py
set /p dummy="Press any key to exit..."
exit /b 0