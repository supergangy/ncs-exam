@echo off
rem  Creates desktop shortcuts for the two launchers. Run once.
chcp 65001 >nul
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ws = New-Object -ComObject WScript.Shell;" ^
  "$desk = [Environment]::GetFolderPath('Desktop');" ^
  "$here = (Get-Location).Path;" ^
  "foreach ($p in @(@('수집기 켜기','후기 수집기를 켜고 설치 페이지를 엽니다',21)," ^
  "                 @('후기 현황 보기','기관별 수집 현황과 소재 브리프를 봅니다',43))) {" ^
  "  $s = $ws.CreateShortcut((Join-Path $desk ($p[0] + '.lnk')));" ^
  "  $s.TargetPath = Join-Path $here ($p[0] + '.bat');" ^
  "  $s.WorkingDirectory = $here;" ^
  "  $s.Description = $p[1];" ^
  "  $s.IconLocation = \"$env:SystemRoot\system32\shell32.dll,$($p[2])\";" ^
  "  $s.Save();" ^
  "  Write-Host ('  만들었습니다  ' + $p[0] + '.lnk') }"

echo.
echo   Done. Check your Desktop.
pause
