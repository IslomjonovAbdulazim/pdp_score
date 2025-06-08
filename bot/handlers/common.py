# bot/handlers/common.py
import logging
from telegram import Update
from telegram.ext import ContextTypes
from bot.middlewares.auth import auth
from services.user_service import UserService

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user

    # Get user role
    role = await auth.get_user_role(update, context)

    if not role:
        await update.message.reply_text(
            "👋 Welcome! Your account is not registered or you don't have access to this bot.\n\n"
            "📞 Contact your administrator or teacher for access."
        )
        return

    # Role-specific welcome messages
    welcome_messages = {
        'admin': (
            "👨‍💼 **Admin Panel Access**\n\n"
            "Available commands:\n"
            "• `/teachers` - Manage teachers\n"
            "• `/new_teacher` - Create teacher account\n"
            "• `/stats` - System statistics\n"
            "• `/groups` - List all groups\n"
            "• `/help` - Show all commands"
        ),
        'teacher': (
            "👩‍🏫 **Teacher Dashboard**\n\n"
            "Module Management:\n"
            "• `/new_module` - Create new module\n"
            "• `/end_module` - End current module\n"
            "• `/current_module` - View active module\n\n"
            "Class Management:\n"
            "• `/new_group` - Create class group\n"
            "• `/groups` - Your groups\n"
            "• `/students` - Manage students\n\n"
            "Assignment & Grading:\n"
            "• `/new_assignment` - Create homework\n"
            "• `/grade` - Grade submissions\n"
            "• `/leaderboard` - View rankings\n\n"
            "Type `/help` for full command list"
        ),
        'student': (
            "📚 **Student Portal**\n\n"
            "Available commands:\n"
            "• `/submit` - Submit homework\n"
            "• `/grades` - View your grades\n"
            "• `/rank` - Check your ranking\n"
            "• `/modules` - View modules\n"
            "• `/last_grade` - Latest grade\n\n"
            "💡 Use `/submit` to upload your homework when assignments are active!"
        )
    }

    await update.message.reply_text(
        welcome_messages[role],
        parse_mode='Markdown'
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    role = await auth.get_user_role(update, context)

    if not role:
        await update.message.reply_text("❌ Access denied. Contact administrator.")
        return

    help_messages = {
        'admin': (
            "🔧 **Admin Commands**\n\n"
            "**Teacher Management:**\n"
            "• `/teachers` - List all teachers\n"
            "• `/new_teacher` - Create teacher account\n\n"
            "**System Overview:**\n"
            "• `/stats` - System statistics\n"
            "• `/groups` - List all groups\n\n"
            "**General:**\n"
            "• `/start` - Show welcome message\n"
            "• `/help` - This help message"
        ),
        'teacher': (
            "👩‍🏫 **Teacher Commands**\n\n"
            "**Module Management:**\n"
            "• `/new_module` - Create new module\n"
            "• `/end_module` - End current module\n"
            "• `/start_module` - Start new module\n"
            "• `/current_module` - View active module\n"
            "• `/module_history` - Past modules\n\n"
            "**Group Management:**\n"
            "• `/new_group` - Create class group\n"
            "• `/groups` - List your groups\n"
            "• `/select_group {id}` - Switch group\n"
            "• `/current_group` - Active group\n\n"
            "**Student Management:**\n"
            "• `/students` - List students\n"
            "• `/add_student` - Add new student\n"
            "• `/remove_student` - Remove student\n\n"
            "**Assignment & Grading:**\n"
            "• `/new_assignment` - Create assignment\n"
            "• `/done` - Finish file upload\n"
            "• `/grade` - Grade next submission\n"
            "• `/queue` - Check grading queue\n"
            "• `/update_grade` - Modify grade\n"
            "• `/pending` - Pending submissions\n"
            "• `/leaderboard` - View rankings"
        ),
        'student': (
            "📚 **Student Commands**\n\n"
            "**Homework Submission:**\n"
            "• `/submit` - Submit homework\n"
            "• `/done` - Finish submission\n\n"
            "**Progress Tracking:**\n"
            "• `/grades` - View all grades\n"
            "• `/rank` - Current ranking\n"
            "• `/modules` - Available modules\n"
            "• `/last_grade` - Latest grade\n\n"
            "**Information:**\n"
            "• `/start` - Welcome message\n"
            "• `/help` - This help message\n\n"
            "💡 **How to submit:**\n"
            "1. Type `/submit`\n"
            "2. Send up to 5 images\n"
            "3. Type `/done`\n"
            "4. Add explanation text"
        )
    }

    await update.message.reply_text(
        help_messages[role],
        parse_mode='Markdown'
    )


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages based on conversation state"""
    user_data = context.user_data
    state = user_data.get('conversation_state')

    if not state:
        await update.message.reply_text(
            "💬 I didn't understand that. Use `/help` to see available commands."
        )
        return

    # Route to appropriate handler based on state
    if state.startswith('admin_'):
        from bot.handlers import admin
        await admin.handle_conversation_state(update, context)
    elif state.startswith('teacher_'):
        from bot.handlers import teacher
        await teacher.handle_conversation_state(update, context)
    elif state.startswith('student_'):
        from bot.handlers import student
        await student.handle_conversation_state(update, context)
    else:
        # Clear unknown state
        user_data.pop('conversation_state', None)
        await update.message.reply_text(
            "❌ Unknown state. Please start over with a command."
        )


async def handle_file_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle file uploads based on conversation state"""
    user_data = context.user_data
    state = user_data.get('conversation_state')

    if not state:
        await update.message.reply_text(
            "📁 Please use a command first before uploading files.\n"
            "Use `/help` to see available commands."
        )
        return

    # Route to appropriate handler based on state
    if state.startswith('teacher_') and 'assignment' in state:
        from bot.handlers import teacher
        await teacher.handle_assignment_files(update, context)
    elif state.startswith('student_') and 'submit' in state:
        from bot.handlers import student
        await student.handle_submission_files(update, context)
    else:
        await update.message.reply_text(
            "❌ Files not expected in current context. Use `/help` for guidance."
        )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Exception while handling update: {context.error}")

    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ An error occurred while processing your request. Please try again.\n"
            "If the problem persists, contact administrator."
        )


def clear_conversation_state(context: ContextTypes.DEFAULT_TYPE):
    """Helper function to clear conversation state"""
    context.user_data.pop('conversation_state', None)
    context.user_data.pop('temp_data', None)