@echo off
rem ============================================================
rem  Review collector launcher
rem  Content is ASCII only on purpose - cmd parses .bat files with
rem  the active codepage, so Korean here would garble. All Korean
rem  output comes from Python after chcp 65001.
rem ============================================================
chcp 65001 >nul
cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
    echo.
    echo   [ERROR] Python not found on PATH.
    echo   Install Python 3.10+ and make sure "Add to PATH" is checked.
    echo.
    pause
    exit /b 1
)

python reviews\serve.py --open

echo.
echo   Collector stopped.
pause
