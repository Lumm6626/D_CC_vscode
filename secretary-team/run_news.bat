@echo off
chcp 65001 >nul
echo ====================================
echo   新闻助理自动运行
echo ====================================
echo.

cd /d D:\D_CC_vscode\secretary-team
python auto_run_news.py

echo.
echo 按任意键退出...
pause >nul
