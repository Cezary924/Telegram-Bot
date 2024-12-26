Set objFSO = CreateObject("Scripting.FileSystemObject")
Set objShell = CreateObject("Wscript.Shell")

path = objFSO.GetParentFolderName(WScript.ScriptFullName) & "\src\bot.py"
exec = "python3 " & path

WScript.Sleep(5000)

if WScript.Arguments.Count = 0 then
    objShell.Run exec ,2,true
else
    exec = exec & " " & WScript.Arguments(0)
    objShell.Run exec ,2,true
end if