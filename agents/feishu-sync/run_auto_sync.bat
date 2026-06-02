@echo off
cd /d "%~dp0\.."
python -m feishu-sync.server --auto --interval 30
pause
