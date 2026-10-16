@echo off
setlocal
cd /d "%~dp0"
if not exist "%~dp0motion-studio\tools\build.py" if not exist "%~dp0..\tools\build.py" (
  echo.
  echo [!] 압축을 먼저 푼 다음, 풀린 폴더 안에서 Install_MotionStudio.cmd 를 실행하세요.
  echo [!] Please extract the zip first, then run Install_MotionStudio.cmd from the extracted folder.
  echo.
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
echo.
pause
