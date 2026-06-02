@echo off
chcp 65001 >nul
echo ========================================
echo Allergy Clinics 日报自动采集系统
echo ========================================
echo.

cd /d D:\D_CC_vscode\agents\news\allergy-news-daily

echo [%date% %time%] Step 1: 采集过敏专业新闻源...
python allergy_news_sources.py

echo.
echo [%date% %time%] Step 2: 生成日报并发送邮件...
python server.py

echo.
echo ========================================
echo 完成！日报已发送至您的邮箱。
echo ========================================
