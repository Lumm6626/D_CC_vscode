@echo off
REM 获取日期 (使用PowerShell，在切换编码之前)
for /f %%a in ('powershell -Command "Get-Date -Format 'yyyy-MM-dd'"') do set "TODAY=%%a"

chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d D:\D_CC_vscode

set "OUTPUT_DIR=D:\D_CC_vscode\agents\news\medical-device-news\output\%TODAY%"
set "HTML_FILE=%OUTPUT_DIR%\medical_news.html"
if exist "%HTML_FILE%" (
    echo [医疗器械新闻采集] 今日报告已存在，跳过执行
    exit /b 0
)
echo [医疗器械新闻采集] 开始运行...
python D:\D_CC_vscode\agents\news\medical-device-news\server.py
echo [医疗器械新闻采集] 完成
