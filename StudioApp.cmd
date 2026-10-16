@echo off
cd /d "%~dp0"
where pythonw >nul 2>nul && (start "" pythonw tools\app.py & exit /b)
where py >nul 2>nul && (start "" py -3 tools\app.py & exit /b)
python tools\app.py
