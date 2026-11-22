' اجرای بات در پسزمینه روی ویندوز (بدون پنجره کنسول)
Set fso = CreateObject("Scripting.FileSystemObject")
Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = fso.GetParentFolderPath(WScript.ScriptFullName)
If Not fso.FolderExists("logs") Then fso.CreateFolder "logs"
WshShell.Run "cmd /c python run.py > logs\bot.log 2>&1", 0, False
