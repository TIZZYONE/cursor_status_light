@echo off
setlocal
set "SRC=%~dp0"
set "DST=%USERPROFILE%\.cursor"
echo Sync to %DST%
if not exist "%DST%\hooks" mkdir "%DST%\hooks"
copy /Y "%SRC%cursor_light.py" "%DST%\" >nul
copy /Y "%SRC%cursor_light_ui.py" "%DST%\" >nul
copy /Y "%SRC%hooks.json" "%DST%\" >nul
copy /Y "%SRC%hooks\set-status.ps1" "%DST%\hooks\" >nul
copy /Y "%SRC%hooks\set-status.py" "%DST%\hooks\" >nul
copy /Y "%SRC%run_cursor_light.bat" "%DST%\" >nul
copy /Y "%SRC%stop_cursor_light.bat" "%DST%\" >nul
echo Done. Restart traffic light: run_cursor_light.bat
echo If hooks.json changed, restart Cursor once.
