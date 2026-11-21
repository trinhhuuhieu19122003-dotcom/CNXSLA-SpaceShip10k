# Creates "SpaceShip 10K" shortcuts on the Desktop and in the Start menu.
# Double-click "Tao loi tat.bat" in the project folder to run this script.
# Keep this file ASCII-only: Windows PowerShell 5 reads scripts without a BOM as ANSI.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$pythonw = Join-Path $root ".venv\Scripts\pythonw.exe"
$python = Join-Path $root ".venv\Scripts\python.exe"
# Must match WINDOWS_APP_ID in spaceship/app.py: Windows then shows the game icon (not Python's)
# on the taskbar, and pinning the running game pins this shortcut.
$appId = "IamSoftware.SpaceShip10K"

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

# Small helper to write System.AppUserModel.ID into a .lnk file (no PowerShell cmdlet for this).
$appIdCode = @"
using System;
using System.Runtime.InteropServices;
using System.Runtime.InteropServices.ComTypes;

public static class LinkAppId {
    [StructLayout(LayoutKind.Sequential, Pack = 4)]
    struct PropertyKey { public Guid fmtid; public uint pid; }

    [StructLayout(LayoutKind.Explicit, Size = 24)]
    struct PropVariant { [FieldOffset(0)] public ushort vt; [FieldOffset(8)] public IntPtr pointer; }

    [ComImport, Guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IPropertyStore {
        void GetCount(out uint count);
        void GetAt(uint index, out PropertyKey key);
        void GetValue(ref PropertyKey key, out PropVariant value);
        void SetValue(ref PropertyKey key, ref PropVariant value);
        void Commit();
    }

    [ComImport, Guid("00021401-0000-0000-C000-000000000046")]
    class ShellLink { }

    public static void Set(string path, string appId) {
        object link = new ShellLink();
        IPersistFile file = (IPersistFile)link;
        file.Load(path, 2);
        IPropertyStore store = (IPropertyStore)link;
        PropertyKey key = new PropertyKey();
        key.fmtid = new Guid("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3");
        key.pid = 5;
        PropVariant value = new PropVariant();
        value.vt = 31;
        value.pointer = Marshal.StringToCoTaskMemUni(appId);
        try {
            store.SetValue(ref key, ref value);
            store.Commit();
            file.Save(path, true);
        } finally {
            Marshal.FreeCoTaskMem(value.pointer);
            Marshal.ReleaseComObject(link);
        }
    }
}
"@
$canSetAppId = $true
try { Add-Type -TypeDefinition $appIdCode -Language CSharp } catch { $canSetAppId = $false }

$icon = Join-Path $root "assets\icon.ico"
$shell = New-Object -ComObject WScript.Shell
$targets = @(
    [Environment]::GetFolderPath("Desktop"),
    [Environment]::GetFolderPath("Programs")
)
foreach ($dir in $targets) {
    $path = Join-Path $dir "SpaceShip 10K.lnk"
    $link = $shell.CreateShortcut($path)
    $link.TargetPath = $pythonw
    $link.Arguments = "-m spaceship"
    $link.WorkingDirectory = $root
    $link.IconLocation = "$icon,0"
    $link.Description = "SpaceShip 10K - ban phi thuyen dieu khien bang tay"
    $link.Save()
    if ($canSetAppId) {
        try { [LinkAppId]::Set($path, $appId) } catch { Write-Host "  (khong gan duoc App ID: $_)" -ForegroundColor DarkYellow }
    }
    Write-Host "Da tao: $path" -ForegroundColor Green
}
Write-Host "Xong! Bam dup vao icon SpaceShip 10K tren Desktop de choi."
Write-Host "Muon ghim xuong Taskbar: mo game, chuot phai vao icon duoi Taskbar -> Pin to taskbar."
