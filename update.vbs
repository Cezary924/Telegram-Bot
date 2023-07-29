Set objFSO = CreateObject("Scripting.FileSystemObject")
Set objShell = CreateObject("Wscript.Shell")

objShell.CurrentDirectory = objFSO.GetParentFolderName(WScript.ScriptFullName)

exec = "git pull && pip install -r .\requirements.txt"
objShell.Run "cmd /c " & exec, 2, True