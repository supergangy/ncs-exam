# 바탕화면에 런처 바로가기를 만든다. `바탕화면 바로가기 만들기.bat` 이 호출한다.
# .bat 안에 PowerShell 한 줄로 밀어 넣으면 ^ 이스케이프가 깨진다. 파일로 분리한다.
$ErrorActionPreference = 'Stop'

$repo = Split-Path -Parent $PSScriptRoot
$desk = [Environment]::GetFolderPath('Desktop')
$shell = New-Object -ComObject WScript.Shell

$items = @(
    @{ Name = '수집기 켜기';      Desc = '후기 수집기를 켜고 설치 페이지를 엽니다'; Icon = 21 },
    @{ Name = '후기 현황 보기';   Desc = '기관별 수집 현황과 소재 브리프를 봅니다'; Icon = 43 }
)

foreach ($it in $items) {
    $bat = Join-Path $repo ($it.Name + '.bat')
    if (-not (Test-Path $bat)) {
        Write-Host ('  건너뜀  ' + $it.Name + '.bat 이 없습니다')
        continue
    }
    $lnk = $shell.CreateShortcut((Join-Path $desk ($it.Name + '.lnk')))
    $lnk.TargetPath       = $bat
    $lnk.WorkingDirectory = $repo
    $lnk.Description      = $it.Desc
    $lnk.IconLocation     = "$env:SystemRoot\system32\shell32.dll,$($it.Icon)"
    $lnk.Save()
    Write-Host ('  만들었습니다  ' + $it.Name)
}

Write-Host ''
Write-Host "  바탕화면: $desk"
