@echo off

set "python=D:\Outils-SHC\code\Python\python.exe"
set "processing=%CD%\src\web_ui.py"

echo Starting CSB Processing Web UI...
echo Python path: %python%
echo Python script path: %processing%

if not exist "%python%" (
    echo ERROR: Python executable not found at %python%
    pause
    exit /b 1
)

if not exist "%processing%" (
    echo ERROR: Python script not found at %processing%
    pause
    exit /b 1
)

echo Running CSB processing application...
%python% %processing%

if %ERRORLEVEL% neq 0 (
    echo ERROR: Application terminated with error code %ERRORLEVEL%
    pause
) else (
    echo Application closed successfully.
)
