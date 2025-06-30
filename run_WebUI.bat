@echo off

set "python=D:\Outils-SHC\code\Python\python.exe"
set "processing=%CD%\src\nicegui_ui.py"

echo Starting CSB Processing GUI with NiceGUI...
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

echo Running NiceGUI application...
%python% %processing%

if %ERRORLEVEL% neq 0 (
    echo ERROR: Application terminated with error code %ERRORLEVEL%
    pause
) else (
    echo GUI closed successfully.
)
