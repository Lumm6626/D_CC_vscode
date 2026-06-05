@echo off
chcp 65001 >nul

REM 设置Python使用UTF-8编码，防止标题中特殊字符导致UnicodeEncodeError
set PYTHONIOENCODING=utf-8

REM 日志目录
set LOGDIR=D:\D_CC_vscode\agents\news\allergy-news-daily\logs
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

REM 按日期命名日志 (格式: YYYYMMDD.log)
REM 中文Windows: %date% = YYYY/mm/dd
set LOGFILE=%LOGDIR%\%date:~0,4%%date:~5,2%%date:~8,2%.log

echo ========================================
echo Allergy Clinics 日报自动采集系统
echo ========================================
echo 日志文件: %LOGFILE%
echo.

cd /d D:\D_CC_vscode\agents\news\allergy-news-daily

echo [%date% %time%] Step 1: 采集过敏专业新闻源... >> "%LOGFILE%"
python allergy_news_sources.py >> "%LOGFILE%" 2>&1

echo. >> "%LOGFILE%"
echo [%date% %time%] Step 2: 生成日报并发送邮件... >> "%LOGFILE%"
python server.py >> "%LOGFILE%" 2>&1

echo. >> "%LOGFILE%"
echo [%date% %time%] Step 3: 生成美国过敏诊所市场简报... >> "%LOGFILE%"
python run_market_brief.py >> "%LOGFILE%" 2>&1

echo.
echo ========================================
echo 完成！日报及市场简报已发送至您的邮箱。
echo ========================================
