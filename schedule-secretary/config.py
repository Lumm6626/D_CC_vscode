"""
Configuration for Schedule Secretary
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Database
    DATABASE_PATH = os.getenv("DATABASE_PATH", "schedule_secretary.db")

    # Flask
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 5001))

    # Feishu
    FEISHU_APP_ID = os.getenv("FEISHU_APP_ID")
    FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET")
    FEISHU_WEBHOOK_URL = os.getenv("FEISHU_WEBHOOK_URL")

    # 163 Email
    EMAIL_HOST = os.getenv("EMAIL_HOST", "pop.163.com")
    EMAIL_PORT = int(os.getenv("EMAIL_PORT", 995))
    EMAIL_USER = os.getenv("EMAIL_USER")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

    # AI
    CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

    # Reminder Settings
    REMINDER_CHECK_INTERVAL_MINUTES = int(os.getenv("REMINDER_CHECK_INTERVAL_MINUTES", 15))
