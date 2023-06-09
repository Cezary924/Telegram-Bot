Dim objFSO : Set objFSO = CreateObject("Scripting.FileSystemObject")
Set objShell = CreateObject("Wscript.Shell")
path = objFSO.GetParentFolderName(WScript.ScriptFullName) & "\bot\bot.py"
exec = "python3 " & path
WScript.Sleep(5000)
objShell.Run exec ,2,true