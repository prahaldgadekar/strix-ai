Set WshShell = CreateObject("WScript.Shell")
strDesktop = WshShell.SpecialFolders("Desktop")
Set oShortcut = WshShell.CreateShortcut(strDesktop & "\STRIX.lnk")
oShortcut.TargetPath = "wscript.exe"
oShortcut.Arguments = """E:\Strix\START_STRIX.vbs"""
oShortcut.WorkingDirectory = "E:\Strix"
oShortcut.Description = "STRIX AI Assistant"
oShortcut.IconLocation = "shell32.dll,21"
oShortcut.Save
WScript.Echo "Shortcut created on Desktop: " & strDesktop & "\STRIX.lnk"
