@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在启动穗游。请在浏览器打开 http://127.0.0.1:8765
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 app.py
) else (
  if exist "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" (
    "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" app.py
  ) else (
    python app.py
  )
)
pause
