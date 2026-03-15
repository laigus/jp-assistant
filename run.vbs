Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.Run """" & WshShell.CurrentDirectory & "\.venv\Scripts\pythonw.exe"" """ & WshShell.CurrentDirectory & "\main.py""", 0, False
