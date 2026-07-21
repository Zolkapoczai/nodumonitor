@echo off
cd /d "%~dp0"
title NODU Monitor
echo NODU Monitor inditasa...
start "" cmd /c "timeout /t 2 >nul & start http://localhost:5050"
"C:\Users\ZoltanPoczai\AppData\Local\Python\pythoncore-3.14-64\python.exe" server.py
pause
