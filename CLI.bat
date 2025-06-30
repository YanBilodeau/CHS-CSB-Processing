@echo off

set "python=D:\Outils-SHC\code\Python\python.exe"
set "processing=%CD%\src\cli.py"
echo %processing%

rem "%python%" "%processing%" --help

"%python%" "%processing%" D:\Dev\CHS-CSB_Processing\src\ingestion\Lowrance\Tuktoyaktuk --output D:\Dev\CHS-CSB_Processing\Output
rem --waterline 1.4 
rem --apply-water-level False
rem --vessel Tuktoyaktuk 

pause
