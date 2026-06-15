' 绘梨衣 · 静默启动 v4.0（托盘常驻 + 自动后端）
' 启动 绘梨衣_托盘.py（内部自动拉起FastAPI后端）
' 托盘右键菜单：仪表盘/门户/开机自启/退出
' 放入 Windows 启动文件夹可实现开机自启:
'   Win+R → shell:startup → 将此文件快捷方式放入

Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

scriptDir = objFSO.GetParentFolderName(WScript.ScriptFullName)

pythonPath = "C:\Users\25307\.workbuddy\binaries\python\envs\default\Scripts\pythonw.exe"
trayPath = scriptDir & "\绘梨衣_托盘.py"

If objFSO.FileExists(pythonPath) And objFSO.FileExists(trayPath) Then
    objShell.Run """" & pythonPath & """ """ & trayPath & """", 0, False
Else
    MsgBox "绘梨衣启动失败" & vbCrLf & _
           "Python: " & pythonPath & vbCrLf & _
           "托盘: " & trayPath, 48, "绘梨衣"
End If
