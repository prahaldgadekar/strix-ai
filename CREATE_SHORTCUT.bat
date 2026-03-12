@echo off
title STRIX Shortcut Creator

:: Unblock both files so no security warning ever appears
powershell -ExecutionPolicy Bypass -Command "Unblock-File -Path 'E:\Strix\START_STRIX.vbs'"
powershell -ExecutionPolicy Bypass -Command "Unblock-File -Path 'E:\Strix\START_STRIX.bat'"

:: Create shortcut pointing to the VBS (silent, no CMD window)
powershell -ExecutionPolicy Bypass -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\STRIX.lnk');$s.TargetPath='E:\Strix\START_STRIX.vbs';$s.WorkingDirectory='E:\Strix';$s.Description='STRIX AI';$s.Save()"

echo  Done! Shortcut created. No more security warnings.
timeout /t 2 >nul