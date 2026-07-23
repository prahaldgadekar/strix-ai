Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "E:\Strix"

' --- Start Ollama silently ---
WshShell.Run "cmd /c ollama serve", 0, False
WScript.Sleep 4000

' --- Launch STRIX ---
WshShell.Run "cmd /c cd /d E:\Strix && python strix.py", 0, False
