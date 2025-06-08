# bot/bot_setup.py
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from config import Config
from bot.handlers import admin, teacher, student, common
from bot.middlewares.auth import AuthMiddleware

logger = logging.getLogger(__name__)


def setup_bot():
    """Setup and configure the Telegram bot"""

    # Create application
    application = Application.builder().token(Config.BOT_TOKEN).build()

    # Add middleware
    auth_middleware = AuthMiddleware()

    # Common handlers (available to all users)
    application.add_handler(CommandHandler("start", common.start_command))
    application.add_handler(CommandHandler("help", common.help_command))

    # Admin handlers
    application.add_handler(CommandHandler("teachers", admin.list_teachers))
    application.add_handler(CommandHandler("new_teacher", admin.create_teacher_start))
    application.add_handler(CommandHandler("stats", admin.system_stats))
    application.add_handler(CommandHandler("groups", admin.list_groups))

    # Teacher handlers
    application.add_handler(CommandHandler("new_module", teacher.create_module))
    application.add_handler(CommandHandler("end_module", teacher.end_module))
    application.add_handler(CommandHandler("start_module", teacher.start_module))
    application.add_handler(CommandHandler("current_module", teacher.current_module))
    application.add_handler(CommandHandler("module_history", teacher.module_history))

    application.add_handler(CommandHandler("new_group", teacher.create_group_start))
    application.add_handler(CommandHandler("groups", teacher.list_groups))
    application.add_handler(CommandHandler("select_group", teacher.select_group))
    application.add_handler(CommandHandler("current_group", teacher.current_group))

    application.add_handler(CommandHandler("students", teacher.list_students))
    application.add_handler(CommandHandler("add_student", teacher.add_student_start))
    application.add_handler(CommandHandler("remove_student", teacher.remove_student))

    application.add_handler(CommandHandler("new_assignment", teacher.create_assignment_start))
    application.add_handler(CommandHandler("done", teacher.handle_done_command))

    application.add_handler(CommandHandler("grade", teacher.grade_submission))
    application.add_handler(CommandHandler("queue", teacher.check_queue))
    application.add_handler(CommandHandler("update_grade", teacher.update_grade_start))
    application.add_handler(CommandHandler("pending", teacher.pending_submissions))
    application.add_handler(CommandHandler("leaderboard", teacher.show_leaderboard))

    # Student handlers
    application.add_handler(CommandHandler("submit", student.submit_homework_start))
    application.add_handler(CommandHandler("done", student.handle_done_command))
    application.add_handler(CommandHandler("grades", student.view_grades))
    application.add_handler(CommandHandler("rank", student.view_rank))
    application.add_handler(CommandHandler("modules", student.view_modules))
    application.add_handler(CommandHandler("last_grade", student.last_grade))

    # Callback query handlers
    application.add_handler(CallbackQueryHandler(admin.handle_teacher_selection, pattern="^teacher_"))
    application.add_handler(CallbackQueryHandler(admin.handle_teacher_action, pattern="^(delete|edit)_teacher_"))
    application.add_handler(CallbackQueryHandler(teacher.handle_student_selection, pattern="^student_"))
    application.add_handler(CallbackQueryHandler(teacher.handle_group_selection, pattern="^group_"))
    application.add_handler(CallbackQueryHandler(teacher.handle_grade_action, pattern="^grade_"))

    # Message handlers for different conversation states
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        common.handle_text_message
    ))

    application.add_handler(MessageHandler(
        filters.PHOTO | filters.Document.ALL,
        common.handle_file_message
    ))

    # Error handler
    application.add_error_handler(common.error_handler)

    logger.info("Bot setup completed successfully")
    return application