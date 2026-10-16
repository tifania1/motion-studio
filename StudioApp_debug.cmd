@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
echo Motion Studio - debug mode. Keep this window open and send a screenshot if an error appears.
where py >nul 2>nul && (py -3 tools\app.py & goto end)
python tools\app.py
:end
pause
