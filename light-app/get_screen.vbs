' 获取主屏幕尺寸 → 输出 WIDTH HEIGHT
' 用于 start.bat 自动定位光点窗口至右下角
Set o = CreateObject("HTMLFile")
h = o.ParentWindow.Screen.Height
w = o.ParentWindow.Screen.Width
posX = w - 340
posY = h - 400
WScript.Echo posX & "," & posY
