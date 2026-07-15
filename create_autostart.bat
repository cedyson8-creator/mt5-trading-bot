@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0create_autostart.ps1" %*
