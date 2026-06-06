@echo off
chcp 65001 >nul

REM 设置Python使用UTF-8编码，防止标题中特殊字符导致UnicodeEncodeError
set PYTHONIOENCODING=utf-8

REM 日志目录
set LOGDIR=D:\D_CC_vscode\agents\news\pharma-news\logs
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

REM 按日期命名日志 (格式: YYYYMMDD.log)
set LOGFILE=%LOGDIR%\%date:~0,4%%date:~5,2%%date:~8,2%.log

echo ========================================
echo 医药生物制药新闻日报自动采集系统
echo ========================================
echo 日志文件: %LOGFILE%
echo.

cd /d D:\D_CC_vscode\agents\news\pharma-news

echo [%date% %time%] 医药新闻日报开始采集... >> "%LOGFILE%"
python server.py >> "%LOGFILE%" 2>&1

echo.
echo ========================================
echo 完成！医药新闻日报已保存。
echo ========================================
