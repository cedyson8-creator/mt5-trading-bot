@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_background.ps1" %*
