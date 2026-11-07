# 在桌面创建「倒计时器」快捷方式
# 若移动了 timer.html 或想换用其他浏览器，重新运行本脚本即可。

$ErrorActionPreference = 'Stop'

$appDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$html     = Join-Path $appDir 'timer.html'
$desktop  = [Environment]::GetFolderPath('Desktop')
$lnkPath  = Join-Path $desktop '倒计时器.lnk'

if (-not (Test-Path $html)) { throw "找不到 $html" }

# 图标：优先用 make_icon.py 生成的 timer-icon.ico
$icon = @('timer-icon.ico', 'app-icon.ico', 'icon.ico') |
        ForEach-Object { Join-Path $appDir $_ } |
        Where-Object { Test-Path $_ } | Select-Object -First 1

# 关键：如果图标文件带「低完整性级别」(Low Mandatory Level)——在 DSH 沙箱工作区里
# 创建的文件都会被打上这个标记——Windows 外壳会拒绝从中加载图标资源，快捷方式就会
# 退化成一张通用白纸图标。这里把完整性级别提升到 Medium。
if ($icon) {
  try {
    & icacls $icon /setintegritylevel Medium 2>$null | Out-Null
  } catch {
    Write-Warning "无法调整图标完整性级别，快捷方式图标可能显示为通用白纸: $($_.Exception.Message)"
  }
}

# 优先 Edge（系统自带），其次 Chrome（当前用户安装）
$candidates = @(
  "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
  "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
  "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
  "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
  "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
)
$browser = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1

$shell = New-Object -ComObject WScript.Shell
$lnk = $shell.CreateShortcut($lnkPath)

if ($browser) {
  $url = 'file:///' + ($html -replace '\\', '/')
  $lnk.TargetPath       = $browser
  $lnk.Arguments        = "--app=`"$url`" --window-size=1140,880 --no-first-run"
  $lnk.WorkingDirectory = $appDir
}
else {
  # 没找到 Chromium 浏览器时，直接交给默认程序打开
  $lnk.TargetPath       = $html
  $lnk.WorkingDirectory = $appDir
}

$lnk.Description = '极简多路倒计时器'
if ($icon) { $lnk.IconLocation = "$icon,0" }
$lnk.Save()

Write-Host "快捷方式已创建: $lnkPath"
if ($browser) { Write-Host "浏览器: $browser" }
if ($icon) { Write-Host "图标: $icon" }
