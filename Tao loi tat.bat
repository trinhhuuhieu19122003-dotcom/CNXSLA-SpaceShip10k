@echo off
rem Tao loi tat SpaceShip 10K tren Desktop va Start menu (chi can chay 1 lan).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\create_shortcut.ps1"
pause
