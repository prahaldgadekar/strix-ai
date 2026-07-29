Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

WshShell.CurrentDirectory = "E:\Strix"

' --- Ensure Ollama is running silently ---
WshShell.Run "cmd /c ollama serve", 0, False
WScript.Sleep 2000

' --- Lightweight Auto-Restart Supervisor Loop ---
' Uses native wscript.exe (~1.5 MB RAM, 0% CPU)
Do
    ' Check if user placed a stop flag to pause auto-restarting
    If fso.FileExists("E:\Strix\STOP_SUPERVISOR.flag") Then
        WScript.Quit
    End If

    ' Launch STRIX and wait for process to finish
    ' True = wait until python strix.py exits before continuing loop
    WshShell.Run "python strix.py", 0, True

    ' 3-second delay before restarting session
    WScript.Sleep 3000
Loop
