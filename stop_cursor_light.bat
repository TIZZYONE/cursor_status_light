@echo off
setlocal
taskkill /f /im mshta.exe >nul 2>nul
for /f "tokens=2" %%p in ('wmic process where "CommandLine like '%%cursor_light.py%%'" get ProcessId /value 2^>nul ^| find "="') do taskkill /f /pid %%p >nul 2>nul
if exist "%USERPROFILE%\.cursor\cursor_light.pid" del /f /q "%USERPROFILE%\.cursor\cursor_light.pid"
echo 已关闭 Cursor 红绿灯
pause
