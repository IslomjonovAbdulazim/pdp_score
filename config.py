import os
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class BotConfig:
    """
    Centralized configuration for the education bot.
    This configuration reads from environment variables (.env file) which makes
    deployment secure and flexible across different environments.
    """

    # Core Bot Configuration - Read from your .env file
    BOT_TOKEN = os.getenv('BOT_TOKEN')  # Your bot token from BotFather

    # Admin Authentication - Uses ADMIN_TEL from your .env file
    ADMIN_PHONE = os.getenv('ADMIN_TEL')  # Note: using ADMIN_TEL to match your .env

    # Group IDs for Authentication - Matches your .env structure
    TEACHERS_GROUP_ID = os.getenv('TEACHER_GROUP_ID')  # Where teachers must be members
    ADMIN_GROUP_ID = os.getenv('ADMIN_GROUP_ID')  # Optional admin group for extra verification

    # Database Configuration
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'education_bot.db')  # Default if not specified

    # File Upload Limits - Uses your .env MAX_FILE_UPLOADS setting
    MAX_PHOTOS_PER_TASK = int(os.getenv('MAX_FILE_UPLOADS', 5))
    MAX_PHOTOS_PER_SUBMISSION = int(os.getenv('MAX_FILE_UPLOADS', 5))

    # Explanation and Content Limits
    MAX_EXPLANATION_LENGTH = int(os.getenv('MAX_EXPLANATION_LENGTH', 200))

    # Grading System Configuration
    MAX_GRADE = int(os.getenv('DEFAULT_MAX_POINTS', 100))  # Uses your default max points
    MIN_GRADE = 0
    LATE_PENALTY_RATE = float(os.getenv('LATE_PENALTY_RATE', 0.3))  # For future late submission feature

    # Bot command texts in Uzbek (since students learn in Uzbek)
    COMMANDS = {
        'start': '/start',
        'menu': '🏠 Asosiy menyu',
        'admin_menu': '👤 Admin paneliga qaytish',
        'teacher_menu': '👨‍🏫 O\'qituvchi paneliga qaytish',
        'student_menu': '👨‍🎓 Talaba paneliga qaytish',
    }

    # Button texts for different user types - All in Uzbek for consistency
    BUTTONS = {
        # Admin buttons - Functions for managing the educational system
        'create_teacher': '➕ Yangi o\'qituvchi qo\'shish',
        'view_teachers': '👥 Barcha o\'qituvchilar',
        'delete_teacher': '🗑 O\'qituvchini o\'chirish',

        # Teacher buttons - Core educational workflow functions
        'create_group': '➕ Yangi guruh yaratish',
        'my_groups': '📚 Mening guruhlarim',
        'create_module': '📝 Yangi modul yaratish',
        'create_task': '📋 Vazifa berish',
        'grade_submissions': '✅ Ishlarni baholash',
        'add_student': '👤 Talaba qo\'shish',
        'remove_student': '❌ Talabani o\'chirish',
        'back_to_groups': '⬅️ Guruhlarga qaytish',

        # Student buttons - Learning and progress tracking functions
        'current_task': '📋 Joriy vazifa',
        'submit_task': '📤 Ish topshirish',
        'my_progress': '📊 Mening natijam',
        'leaderboard': '🏆 Reytinglar',

        # Role Selection buttons - For users with multiple roles
        'select_admin_role': '👨‍💼 Admin sifatida kirish',
        'select_teacher_role': '👨‍🏫 O\'qituvchi sifatida kirish',
        'select_student_role': '👨‍🎓 Talaba sifatida kirish',
        'switch_role': '🔄 Rolni o\'zgartirish',

        # Common navigation buttons used across all user types
        'back': '⬅️ Orqaga',
        'cancel': '❌ Bekor qilish',
        'confirm': '✅ Tasdiqlash',
        'next': '➡️ Keyingisi',
        'done': '✅ Tayyor',
    }

    # Message templates in Uzbek - Provides consistent user experience
    MESSAGES = {
        # Welcome messages - First impression for different user types
        'welcome_admin': '👋 Assalomu alaykum! Siz admin sifatida tizimga kirdingiz.',
        'welcome_teacher': '👋 Assalomu alaykum! Siz o\'qituvchi sifatida tizimga kirdingiz.',
        'welcome_student': '👋 Assalomu alaykum! Siz talaba sifatida tizimga kirdingiz.',

        # Authentication messages - Guide users through verification process
        'phone_request': '📱 Iltimos, telefon raqamingizni yuboring:',
        'contact_button': '📱 Telefon raqamimni yuborish',
        'auth_failed': '❌ Sizning raqamingiz tizimda ro\'yxatdan o\'tmagan. Qo\'llab-quvvatlash bilan bog\'laning.',
        'not_in_group': '❌ Siz kerakli guruhda emassiz. Avval guruhga qo\'shiling.',

        # Success messages - Positive feedback for completed actions
        'teacher_created': '✅ O\'qituvchi muvaffaqiyatli yaratildi!',
        'group_created': '✅ Guruh muvaffaqiyatli yaratildi!',
        'module_created': '✅ Yangi modul yaratildi!',
        'task_created': '✅ Vazifa muvaffaqiyatli yuborildi!',
        'student_added': '✅ Talaba guruhga qo\'shildi!',
        'submission_received': '✅ Sizning ishingiz qabul qilindi!',
        'graded_successfully': '✅ Baho qo\'yildi!',

        # Error messages - Clear guidance when things go wrong
        'something_wrong': '❌ Xatolik yuz berdi. Qaytadan urinib ko\'ring.',
        'no_permission': '❌ Sizda bu amalni bajarish uchun ruxsat yo\'q.',
        'already_submitted': '❌ Siz allaqachon ish topshirgansiz!',
        'no_active_task': '🎉 Hozirda faol vazifa yo\'q. Eng so\'nggi bahoyingizdan zavqlaning!',
        'contact_support': '📞 Qo\'llab-quvvatlash bilan bog\'laning yoki o\'qituvchingizga murojaat qiling.',

        # Input prompts - Clear instructions for data collection
        'enter_teacher_name': '👤 O\'qituvchining to\'liq ismini kiriting:',
        'enter_teacher_phone': '📱 O\'qituvchining telefon raqamini kiriting:',
        'enter_group_name': '📚 Guruh nomini kiriting:',
        'enter_channel_id': '🆔 Telegram kanal ID sini kiriting:',
        'enter_student_name': '👤 Talabaning to\'liq ismini kiriting:',
        'enter_student_phone': '📱 Talabaning telefon raqamini kiriting:',
        'enter_task_description': '📝 Vazifa tavsifini kiriting:',
        'send_task_photos': '📸 Vazifa uchun rasmlar yuboring (ixtiyoriy):',
        'enter_grade': '📊 Bahoni kiriting (0-100):',
        'submission_description': '📝 Ish haqida qisqacha ma\'lumot yuboring:',
        'send_submission_photos': '📸 Ish rasmlarini yuboring:',
    }

    @staticmethod
    def is_admin(phone_number):
        """
        Check if the given phone number belongs to admin.
        This is the primary admin authentication method using phone verification.
        """
        admin_phone = BotConfig.ADMIN_PHONE
        if not admin_phone:
            print("WARNING: ADMIN_TEL not set in environment variables!")
            return False
        return phone_number == admin_phone

    @staticmethod
    def format_phone(phone_number):
        """
        Standardize phone number format for consistent comparison.
        This handles different input formats and converts them to international format.

        Examples:
        - "998901234567" becomes "+998901234567"
        - "901234567" becomes "+998901234567"
        - "+998 90 123 45 67" becomes "+998901234567"
        """
        # Remove all non-digit characters except +
        clean_phone = ''.join(c for c in phone_number if c.isdigit() or c == '+')

        # If it doesn't start with +, assume it's local and add +998
        if not clean_phone.startswith('+'):
            if clean_phone.startswith('998'):
                clean_phone = '+' + clean_phone
            else:
                clean_phone = '+998' + clean_phone

        return clean_phone

    @staticmethod
    def photos_to_json(photo_list):
        """
        Convert list of photo file_ids to JSON string for database storage.
        This allows us to store multiple photos efficiently in a single database field.
        """
        if not photo_list:
            return None
        return json.dumps(photo_list)

    @staticmethod
    def json_to_photos(json_string):
        """
        Convert JSON string back to list of photo file_ids.
        This retrieves the photo list from database storage for display.
        """
        if not json_string:
            return []
        try:
            return json.loads(json_string)
        except:
            return []

    @staticmethod
    def get_queue_position_text(position):
        """
        Get user-friendly queue position text in Uzbek.
        This provides encouraging feedback to students about their submission status.
        """
        if position == 1:
            return "Sizning ishingiz keyingi navbatda!"
        else:
            return f"Sizning navbatingiz: {position}"

    @staticmethod
    def validate_configuration():
        """
        Validate that all required environment variables are set.
        This helps catch configuration errors early during startup.
        """
        required_vars = {
            'BOT_TOKEN': BotConfig.BOT_TOKEN,
            'ADMIN_TEL': BotConfig.ADMIN_PHONE,
            'TEACHER_GROUP_ID': BotConfig.TEACHERS_GROUP_ID
        }

        missing_vars = [var for var, value in required_vars.items() if not value]

        if missing_vars:
            print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
            print("Please check your .env file and ensure all required variables are set.")
            return False

        print("✅ Configuration validation passed!")
        return True


# Create a global config instance for easy import across the application
config = BotConfig()