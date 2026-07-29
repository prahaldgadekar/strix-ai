@echo off
echo =========================================
echo  Stopping STRIX Supervisor & Auto-Restart
echo =========================================
echo.
taskkill /FI "WINDOWTITLE eq STRIX*" /F 2>nul
taskkill /IM wscript.exe /F 2>nul
echo STRIX Supervisor stopped.
pause
