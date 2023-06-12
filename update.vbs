Set objFSO = CreateObject("Scripting.FileSystemObject")
Set objShell = CreateObject("Wscript.Shell")

objShell.CurrentDirectory = objFSO.GetParentFolderName(WScript.ScriptFullName)

exec = "git pull"
objShell.Run exec ,2,true