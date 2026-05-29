# Cursor 红绿灯 — 一键安装到用户目录
$ErrorActionPreference = 'Stop'
$Repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$Target = Join-Path $env:USERPROFILE '.cursor'
$HooksDir = Join-Path $Target 'hooks'

Write-Host '=== Cursor 红绿灯 安装 ===' -ForegroundColor Cyan

New-Item -ItemType Directory -Path $Target -Force | Out-Null
New-Item -ItemType Directory -Path $HooksDir -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $Target 'status') -Force | Out-Null

$files = @(
  'cursor_light.py',
  'cursor_light_ui.py',
  'hooks.json',
  'run_cursor_light.bat',
  'stop_cursor_light.bat'
)
foreach ($f in $files) {
  Copy-Item (Join-Path $Repo $f) (Join-Path $Target $f) -Force
  Write-Host "  已复制 $f"
}
Copy-Item (Join-Path $Repo 'hooks\set-status.ps1') (Join-Path $HooksDir 'set-status.ps1') -Force
Copy-Item (Join-Path $Repo 'hooks\set-status.py') (Join-Path $HooksDir 'set-status.py') -Force
Write-Host '  已复制 hooks\set-status.ps1 / set-status.py'

# Python 依赖
Write-Host '正在安装 Python 依赖...' -ForegroundColor Yellow
python -m pip install -r (Join-Path $Repo 'requirements.txt') -q
if ($LASTEXITCODE -ne 0) {
  Write-Host 'pip 安装失败，请确认已安装 Python 3' -ForegroundColor Red
  exit 1
}

# 桌面快捷方式（可选）
$desktop = [Environment]::GetFolderPath('Desktop')
$lnkStart = Join-Path $desktop 'Cursor红绿灯-启动.lnk'
$lnkStop = Join-Path $desktop 'Cursor红绿灯-关闭.lnk'
try {
  $wsh = New-Object -ComObject WScript.Shell
  $s = $wsh.CreateShortcut($lnkStart)
  $s.TargetPath = Join-Path $Target 'run_cursor_light.bat'
  $s.WorkingDirectory = $Target
  $s.Save()
  $s2 = $wsh.CreateShortcut($lnkStop)
  $s2.TargetPath = Join-Path $Target 'stop_cursor_light.bat'
  $s2.WorkingDirectory = $Target
  $s2.Save()
    Write-Host '  Desktop shortcuts created'
} catch {
  Write-Host '  Skip desktop shortcuts'
}

Write-Host ''
Write-Host 'Done! Next steps:' -ForegroundColor Green
Write-Host '  1. Restart Cursor completely'
Write-Host '  2. Run run_cursor_light.bat or desktop shortcut'
Write-Host '  3. Tray menu: topmost / opacity / exit'
Write-Host ''
Start-Process (Join-Path $Target 'run_cursor_light.bat')
