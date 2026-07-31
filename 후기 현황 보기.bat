@echo off
rem  Review DB status - collection matrix + topic brief per institution.
chcp 65001 >nul
cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] Python not found on PATH.
    pause
    exit /b 1
)

python reviews\report.py --matrix

rem  Print a topic brief for every institution that has reviews.
for /f "usebackq delims=" %%O in (`python -c "import json,pathlib;p=pathlib.Path('reviews/db.json');print('\n'.join(sorted({r['org'] for r in json.loads(p.read_text(encoding='utf-8'))}))) if p.exists() else None"`) do (
    python reviews\report.py --brief "%%O"
)

echo.
pause
