@echo off
REM Inkscape AI - one-click installer (Windows).
REM Runs install.ps1, bypassing PowerShell execution policy for this run only.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
