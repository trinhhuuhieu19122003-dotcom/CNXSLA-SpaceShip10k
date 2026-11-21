# Creates "SpaceShip 10K" shortcuts on the Desktop and in the Start menu.
# Double-click "Tao loi tat.bat" in the project folder to run this script.
# Keep this file ASCII-only: Windows PowerShell 5 reads scripts without a BOM as ANSI.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$pythonw = Join-Path $root ".venv\Scripts\pythonw.exe"
$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $pythonw)) {
    Write-Host "Khong tim thay $pythonw" -ForegroundColor Red
    Write-Host "Hay tao moi truong truoc:  py -3.11 -m venv .venv"
    exit 1
}
& $python -c "import pygame, cv2, mediapipe, numpy" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Dang cai thu vien (lan dau mat vai phut)..." -ForegroundColor Yellow
    & $python -m pip install -r (Join-Path $root "requirements.txt")
    if ($LASTEXITCODE -ne 0) { Write-Host "Cai thu vien that bai." -ForegroundColor Red; exit 1 }
}
$icon = Join-Path $root "assets\icon.ico"
$shell = New-Object -ComObject WScript.Shell
$targets = @(
    [Environment]::GetFolderPath("Desktop"),
    [Environment]::GetFolderPath("Programs")
)
foreach ($dir in $targets) {
    $link = $shell.CreateShortcut((Join-Path $dir "SpaceShip 10K.lnk"))
    $link.TargetPath = $pythonw
    $link.Arguments = "-m spaceship"
    $link.WorkingDirectory = $root
    $link.IconLocation = "$icon,0"
    $link.Description = "SpaceShip 10K - ban phi thuyen dieu khien bang tay"
    $link.Save()
    Write-Host "Da tao: $(Join-Path $dir 'SpaceShip 10K.lnk')" -ForegroundColor Green
}
Write-Host "Xong! Bam dup vao icon SpaceShip 10K tren Desktop de choi."
