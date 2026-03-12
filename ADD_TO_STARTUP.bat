@echo off
title Add STRIX Wake Listener to Windows Startup
color 0B

echo.
echo  Adding STRIX Wake Listener to Windows startup...
echo  (This makes STRIX listen for your voice even when PC just boots)
echo.

set LISTENER=E:\Strix\STRIX_WAKE_LISTENER.pyw
set STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup

:: Copy the listener to startup folder
copy "%LISTENER%" "%STARTUP%\STRIX_WAKE_LISTENER.pyw" >nul

if exist "%STARTUP%\STRIX_WAKE_LISTENER.pyw" (
    echo  SUCCESS! Wake listener added to startup.
    echo.
    echo  From now on:
    echo  - Boot your PC
    echo  - Say "hey strix" or "wake up strix"
    echo  - STRIX opens automatically. No clicking needed.
    echo.
) else (
    echo  ERROR. Try running as Administrator.
)
pause
