@echo off
schtasks /delete /tn "AllergyDailyReport" /f 2>nul
schtasks /create /tn "AllergyDailyReport" /tr "D:\D_CC_vscode\agents\news\allergy-news-daily\run_allergy_daily.bat" /sc daily /st 10:30 /f
echo Task creation complete.
pause
