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
echo [%date% %time%] Step 3: 生成美国过敏诊所市场简报...
python run_market_brief.py

echo.
echo ========================================
echo 完成！日报及市场简报已发送至您的邮箱。
echo ========================================
