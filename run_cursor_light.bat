@echo off
setlocal
set "DIR=%USERPROFILE%\.cursor"
set "APP=%DIR%\cursor_light.py"
if not exist "%APP%" (
  echo 请先运行 install.bat 安装
  pause
  exit /b 1
)
taskkill /f /im mshta.exe >nul 2>nul
for /f "tokens=2" %%p in ('wmic process where "CommandLine like '%%cursor_light.py%%'" get ProcessId /value 2^>nul ^| find "="') do taskkill /f /pid %%p >nul 2>nul
start "" pythonw "%APP%"
exit /b 0
