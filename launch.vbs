Set oWS = CreateObject("WScript.Shell")
scriptDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
oWS.CurrentDirectory = scriptDir
oWS.Run "pythonw.exe """ & scriptDir & "\run.py""", 0, False
