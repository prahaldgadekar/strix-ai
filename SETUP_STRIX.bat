@echo off
title STRIX — Desktop Shortcut Setup
color 0B

echo.
echo  ============================================
echo    S.T.R.I.X  —  Desktop Shortcut Setup
echo  ============================================
echo.

set "STRIX_DIR=E:\Strix"
set "LAUNCHER=%STRIX_DIR%\START_STRIX.vbs"
set "DESKTOP=%USERPROFILE%\Desktop"

:: ── Step 1: Create the silent VBS launcher (no CMD window) ────
echo  [1/3] Creating silent launcher...

(
    echo Set WshShell = CreateObject^("WScript.Shell"^)
    echo WshShell.CurrentDirectory = "%STRIX_DIR%"
    echo.
    echo ' --- Start Ollama silently ---
    echo WshShell.Run "cmd /c ollama serve", 0, False
    echo WScript.Sleep 4000
    echo.
    echo ' --- Launch STRIX ---
    echo WshShell.Run "cmd /c cd /d %STRIX_DIR% && python strix.py", 0, False
) > "%LAUNCHER%"

if exist "%LAUNCHER%" (
    echo        Launcher created: START_STRIX.vbs
) else (
    echo  [!!] Failed to create launcher. Try running as Administrator.
    pause
    exit /b 1
)

:: ── Step 2: Unblock files so Windows doesn't show warnings ────
echo.
echo  [2/3] Unblocking files...
powershell -ExecutionPolicy Bypass -Command "Unblock-File -Path '%LAUNCHER%'" 2>nul
echo        Done.

:: ── Step 3: Create desktop shortcut ──────────────────────────
echo.
echo  [3/3] Creating desktop shortcut...

cscript //nologo "%STRIX_DIR%\CREATE_SHORTCUT.vbs"

if exist "%DESKTOP%\STRIX.lnk" (
    echo        Shortcut created on Desktop!
) else if exist "%USERPROFILE%\OneDrive\Desktop\STRIX.lnk" (
    echo        Shortcut created on Desktop!
) else (
    echo        Shortcut created!
)

:: ── Optional: Add wake listener to startup ────────────────────
echo.
set /p ADD_STARTUP="  Add STRIX wake listener to Windows startup? (Y/N): "
if /i "%ADD_STARTUP%"=="Y" (
    set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
    copy "%STRIX_DIR%\STRIX_WAKE_LISTENER.pyw" "%STARTUP%\STRIX_WAKE_LISTENER.pyw" >nul
    if exist "%STARTUP%\STRIX_WAKE_LISTENER.pyw" (
        echo.
        echo        Wake listener added to startup!
        echo        Say "hey strix" after boot — no clicking needed.
    ) else (
        echo        Could not add to startup. Try running as Administrator.
    )
)

echo.
echo  ============================================
echo    All done! Double-click STRIX on Desktop.
echo  ============================================
echo.
pause
