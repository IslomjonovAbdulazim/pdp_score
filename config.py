# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    # Telegram Bot Configuration
    BOT_TOKEN = os.getenv('BOT_TOKEN')

    # Group IDs for authentication
    ADMIN_GROUP_ID = int(os.getenv('ADMIN_GROUP_ID', '0'))
    TEACHER_GROUP_ID = int(os.getenv('TEACHER_GROUP_ID', '0'))

    # Database Configuration
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'data/bot.db')

    # System Settings
    MAX_FILE_UPLOADS = int(os.getenv('MAX_FILE_UPLOADS', '5'))
    MAX_EXPLANATION_LENGTH = int(os.getenv('MAX_EXPLANATION_LENGTH', '200'))
    DEFAULT_MAX_POINTS = int(os.getenv('DEFAULT_MAX_POINTS', '20'))
    LATE_PENALTY_RATE = float(os.getenv('LATE_PENALTY_RATE', '0.3'))  # 30% penalty

    # Validation
    @classmethod
    def validate_config(cls):
        """Validate required configuration"""
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is required")

        if cls.ADMIN_GROUP_ID == 0:
            raise ValueError("ADMIN_GROUP_ID is required")

        if cls.TEACHER_GROUP_ID == 0:
            raise ValueError("TEACHER_GROUP_ID is required")

        print("✅ Configuration validated successfully")

    @classmethod
    def display_config(cls):
        """Display current configuration (without sensitive data)"""
        print("Current Configuration:")
        print(f"  Admin Group ID: {cls.ADMIN_GROUP_ID}")
        print(f"  Teacher Group ID: {cls.TEACHER_GROUP_ID}")
        print(f"  Max File Uploads: {cls.MAX_FILE_UPLOADS}")
        print(f"  Max Explanation Length: {cls.MAX_EXPLANATION_LENGTH}")
        print(f"  Default Max Points: {cls.DEFAULT_MAX_POINTS}")
        print(f"  Late Penalty Rate: {cls.LATE_PENALTY_RATE * 100}%")


# Initialize and validate config on import
try:
    Config.validate_config()
except ValueError as e:
    print(f"❌ Configuration Error: {e}")
    print("Please check your .env file and ensure all required variables are set.")