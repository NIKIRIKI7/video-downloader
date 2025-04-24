@echo off
setlocal enabledelayedexpansion

echo Generating report... > output.txt

for /r %%i in (*.py) do (
    echo [File: %%i] >> output.txt
    type "%%i" >> output.txt
    echo. >> output.txt
    echo ======================================= >> output.txt
    echo. >> output.txt
)

echo Done! Check output.txt.
pause