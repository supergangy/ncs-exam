@echo off
rem  Creates desktop shortcuts for the two launchers. Run once.
rem  The actual work lives in tools\make_shortcuts.ps1 - inlining PowerShell
rem  here would need ^ line continuations, which break on nested quotes.
chcp 65001 >nul
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "tools\make_shortcuts.ps1"

echo.
pause
