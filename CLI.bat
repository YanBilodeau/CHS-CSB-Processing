@echo off

set "python=D:\Outils-SHC\code\Python\python.exe"
set "processing=%CD%\src\cli.py"
echo %processing%

rem "%python%" "%processing%" process --help

"%python%" "%processing%" process D:\Dev\CHS-CSB_Processing\src\ingestion\Lowrance\Tuktoyaktuk --output D:\Dev\CHS-CSB_Processing\Output --excluded-stations 06525 --excluded-stations 03755
rem --waterline 1.4 
rem --apply-water-level False
rem --vessel Tuktoyaktuk 

rem "%python%" "%processing%" convert --help

rem "%python%" "%processing%" convert D:\Dev\CHS-CSB_Processing\Output\Data\CH-Lowrance-unknown-20220813-20221105.geojson D:\Dev\CHS-CSB_Processing\Output\Data\CH-Lowrance-unknown-20220813-20221105.gpkg --output D:\Dev\CHS-CSB_Processing\Output\Convert --format csar --format geotiff --format geojson

pause
