# bot/middlewares/auth.py
import logging
from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes
from config import Config
from services.user_service import UserService

logger = logging.getLogger(__name__)


class AuthMiddleware:
    """Authentication middleware for verifying user permissions"""

    def __init__(self):
        self.user_service = UserService()

    async def check_group_membership(self, context: ContextTypes.DEFAULT_TYPE,
                                     user_id: int, group_id: int) -> bool:
        """Check if user is member of specific group"""
        try:
            member = await context.bot.get_chat_member(group_id, user_id)
            return member.status in ['member', 'administrator', 'creator']
        except Exception as e:
            logger.error(f"Error checking group membership: {e}")
            return False

    async def verify_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Verify if user is admin"""
        user_id = update.effective_user.id

        # Check if user is in admin group
        if not await self.check_group_membership(context, user_id, Config.ADMIN_GROUP_ID):
            await update.message.reply_text("❌ Access denied. Admin privileges required.")
            return False

        # Check if user is registered admin in database
        admin = self.user_service.get_user_by_telegram_id(user_id)
        if not admin or admin['role'] != 'admin':
            await update.message.reply_text("❌ Admin account not found. Contact system administrator.")
            return False

        return True

    async def verify_teacher(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Verify if user is teacher"""
        user_id = update.effective_user.id

        # Check if user is in teacher group
        if not await self.check_group_membership(context, user_id, Config.TEACHER_GROUP_ID):
            await update.message.reply_text("❌ Access denied. Teacher privileges required.")
            return False

        # Check if user is registered teacher in database
        teacher = self.user_service.get_user_by_telegram_id(user_id)
        if not teacher or teacher['role'] != 'teacher':
            await update.message.reply_text("❌ Teacher account not found. Contact administrator.")
            return False

        return True

    async def verify_student(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Verify if user is student"""
        user_id = update.effective_user.id

        # Get student from database
        student = self.user_service.get_user_by_telegram_id(user_id)
        if not student or student['role'] != 'student':
            await update.message.reply_text("❌ Student account not found. Contact your teacher.")
            return False

        # Check if student is in their class group
        class_group_id = student['telegram_group_id']
        if not await self.check_group_membership(context, user_id, class_group_id):
            await update.message.reply_text("❌ Access denied. You must be in your class group.")
            return False

        return True

    async def get_user_role(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[str]:
        """Get user role based on group membership and database"""
        user_id = update.effective_user.id

        # Check database first
        user = self.user_service.get_user_by_telegram_id(user_id)
        if not user:
            return None

        # Verify group membership based on role
        if user['role'] == 'admin':
            if await self.check_group_membership(context, user_id, Config.ADMIN_GROUP_ID):
                return 'admin'
        elif user['role'] == 'teacher':
            if await self.check_group_membership(context, user_id, Config.TEACHER_GROUP_ID):
                return 'teacher'
        elif user['role'] == 'student':
            if await self.check_group_membership(context, user_id, user['telegram_group_id']):
                return 'student'

        return None


# Global auth instance
auth = AuthMiddleware()