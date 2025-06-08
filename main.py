import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ConversationHandler,
    ContextTypes, filters
)

# Import our custom modules
from database import db
from config import config
from auth.auth import auth
from handlers.admin_handlers import admin_handlers, WAITING_TEACHER_NAME, WAITING_TEACHER_PHONE, CONFIRMING_DELETE
from handlers.teacher_handlers import (
    teacher_handlers,
    WAITING_GROUP_NAME, WAITING_CHANNEL_ID, WAITING_STUDENT_NAME, WAITING_STUDENT_PHONE,
    WAITING_TASK_DESCRIPTION, WAITING_TASK_PHOTOS, WAITING_GRADE
)
from handlers.student_handlers import student_handlers, WAITING_SUBMISSION_DESCRIPTION, WAITING_SUBMISSION_PHOTOS

# Configure logging to track bot behavior and debug issues
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation state for phone number collection
WAITING_PHONE = 1


class EducationBot:
    """
    Main orchestrator for our education management system.

    This class ties together all the educational components:
    - User authentication and role determination
    - Message routing based on user type and context
    - Conversation management for complex workflows
    - Error handling and user guidance

    The bot operates as a sophisticated educational assistant that adapts
    its interface and capabilities based on who is using it.
    """

    def __init__(self):
        """Initialize the bot application with all necessary handlers"""
        self.app = Application.builder().token(config.BOT_TOKEN).build()
        self._setup_handlers()

    def _setup_handlers(self):
        """
        Configure all conversation handlers and message routing.
        This is the neural network of our bot - determining how messages flow through the system.
        """

        # Main authentication conversation (handles /start and phone collection)
        auth_conversation = ConversationHandler(
            entry_points=[CommandHandler('start', self.start_command)],
            states={
                WAITING_PHONE: [
                    MessageHandler(filters.CONTACT, self.receive_phone_contact),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_phone_text)
                ]
            },
            fallbacks=[CommandHandler('start', self.start_command)]
        )

        # Admin workflow conversations
        admin_teacher_conversation = ConversationHandler(
            entry_points=[MessageHandler(
                filters.Regex(f"^{config.BUTTONS['create_teacher']}$"),
                admin_handlers.start_create_teacher
            )],
            states={
                WAITING_TEACHER_NAME: [MessageHandler(filters.TEXT, admin_handlers.receive_teacher_name)],
                WAITING_TEACHER_PHONE: [MessageHandler(filters.TEXT, admin_handlers.receive_teacher_phone)]
            },
            fallbacks=[MessageHandler(
                filters.Regex(f"^{config.BUTTONS['cancel']}$"),
                admin_handlers.cancel_operation
            )]
        )

        admin_delete_conversation = ConversationHandler(
            entry_points=[MessageHandler(
                filters.Regex(f"^{config.BUTTONS['delete_teacher']}$"),
                admin_handlers.start_delete_teacher
            )],
            states={
                CONFIRMING_DELETE: [MessageHandler(filters.TEXT, admin_handlers.confirm_delete_teacher)]
            },
            fallbacks=[MessageHandler(
                filters.Regex(f"^{config.BUTTONS['cancel']}$"),
                admin_handlers.cancel_operation
            )]
        )

        # Teacher workflow conversations
        teacher_group_conversation = ConversationHandler(
            entry_points=[MessageHandler(
                filters.Regex(f"^{config.BUTTONS['create_group']}$"),
                teacher_handlers.start_create_group
            )],
            states={
                WAITING_GROUP_NAME: [MessageHandler(filters.TEXT, teacher_handlers.receive_group_name)],
                WAITING_CHANNEL_ID: [MessageHandler(filters.TEXT, teacher_handlers.receive_channel_id)]
            },
            fallbacks=[MessageHandler(
                filters.Regex(f"^{config.BUTTONS['cancel']}$"),
                teacher_handlers.cancel_operation
            )]
        )

        teacher_student_conversation = ConversationHandler(
            entry_points=[MessageHandler(
                filters.Regex(f"^{config.BUTTONS['add_student']}$"),
                teacher_handlers.start_add_student
            )],
            states={
                WAITING_STUDENT_NAME: [MessageHandler(filters.TEXT, teacher_handlers.receive_student_name)],
                WAITING_STUDENT_PHONE: [MessageHandler(filters.TEXT, teacher_handlers.receive_student_phone)]
            },
            fallbacks=[MessageHandler(
                filters.Regex(f"^{config.BUTTONS['cancel']}$"),
                teacher_handlers.cancel_operation
            )]
        )

        teacher_task_conversation = ConversationHandler(
            entry_points=[MessageHandler(
                filters.Regex(f"^{config.BUTTONS['create_task']}$"),
                teacher_handlers.start_create_task
            )],
            states={
                WAITING_TASK_DESCRIPTION: [MessageHandler(filters.TEXT, teacher_handlers.receive_task_description)],
                WAITING_TASK_PHOTOS: [
                    MessageHandler(filters.PHOTO, teacher_handlers.receive_task_photos),
                    MessageHandler(filters.TEXT, teacher_handlers.receive_task_photos)
                ]
            },
            fallbacks=[MessageHandler(
                filters.Regex(f"^{config.BUTTONS['cancel']}$"),
                teacher_handlers.cancel_operation
            )]
        )

        # Student workflow conversations
        student_submission_conversation = ConversationHandler(
            entry_points=[MessageHandler(
                filters.Regex(f"^{config.BUTTONS['submit_task']}$"),
                student_handlers.start_submit_task
            )],
            states={
                WAITING_SUBMISSION_DESCRIPTION: [
                    MessageHandler(filters.TEXT, student_handlers.receive_submission_description)],
                WAITING_SUBMISSION_PHOTOS: [
                    MessageHandler(filters.PHOTO, student_handlers.receive_submission_photos),
                    MessageHandler(filters.TEXT, student_handlers.receive_submission_photos)
                ]
            },
            fallbacks=[MessageHandler(
                filters.Regex(f"^{config.BUTTONS['cancel']}$"),
                student_handlers.cancel_operation
            )]
        )

        # Register all conversation handlers
        self.app.add_handler(auth_conversation)
        self.app.add_handler(admin_teacher_conversation)
        self.app.add_handler(admin_delete_conversation)
        self.app.add_handler(teacher_group_conversation)
        self.app.add_handler(teacher_student_conversation)
        self.app.add_handler(teacher_task_conversation)
        self.app.add_handler(student_submission_conversation)

        # Single-action message handlers (no conversation needed)
        self.app.add_handler(MessageHandler(
            filters.Regex(f"^{config.BUTTONS['view_teachers']}$"),
            admin_handlers.view_all_teachers
        ))
        self.app.add_handler(MessageHandler(
            filters.Regex(f"^{config.BUTTONS['my_groups']}$"),
            teacher_handlers.show_my_groups
        ))
        self.app.add_handler(MessageHandler(
            filters.Regex(f"^{config.BUTTONS['create_module']}$"),
            teacher_handlers.create_new_module
        ))
        self.app.add_handler(MessageHandler(
            filters.Regex(f"^{config.BUTTONS['grade_submissions']}$"),
            teacher_handlers.start_grading
        ))
        self.app.add_handler(MessageHandler(
            filters.Regex(f"^{config.BUTTONS['current_task']}$"),
            student_handlers.show_current_task
        ))
        self.app.add_handler(MessageHandler(
            filters.Regex(f"^{config.BUTTONS['my_progress']}$"),
            student_handlers.show_my_progress
        ))
        self.app.add_handler(MessageHandler(
            filters.Regex(f"^{config.BUTTONS['leaderboard']}$"),
            student_handlers.show_leaderboard
        ))

        # Special handler for teacher grading workflow (handles grade input)
        self.app.add_handler(MessageHandler(
            filters.TEXT & filters.Regex(r'^\d+$'),  # Numbers only for grades
            self.handle_grade_input
        ))

        # Generic message handler for menu navigation and group selection
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message))

        # Error handler for graceful error management
        self.app.add_error_handler(self.error_handler)

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle the /start command - the entry point to our educational system.
        This creates the first impression and guides users through authentication.
        """
        user = update.effective_user

        # Clear any existing context when starting fresh
        context.user_data.clear()

        # Welcome message with clear instructions
        welcome_message = (
            f"👋 Assalomu alaykum, {user.first_name}!\n\n"
            f"Ta'lim boshqaruv tizimiga xush kelibsiz!\n"
            f"Davom etish uchun telefon raqamingizni yuborishingiz kerak.\n\n"
            f"📱 Pastdagi tugmani bosing yoki raqamingizni yozing:"
        )

        # Create contact request keyboard
        keyboard = [[KeyboardButton(config.MESSAGES['contact_button'], request_contact=True)]]
        reply_markup = ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
            one_time_keyboard=True
        )

        await update.message.reply_text(welcome_message, reply_markup=reply_markup)
        return WAITING_PHONE

    async def receive_phone_contact(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle phone number received through contact sharing.
        This is the preferred method as it's more secure and accurate.
        """
        contact = update.message.contact
        phone_number = contact.phone_number

        # Ensure phone starts with + for international format
        if not phone_number.startswith('+'):
            phone_number = '+' + phone_number

        await self._authenticate_user(update, context, phone_number)
        return ConversationHandler.END

    async def receive_phone_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle phone number received as text input.
        This provides an alternative for users who prefer typing.
        """
        phone_number = update.message.text.strip()
        formatted_phone = config.format_phone(phone_number)

        await self._authenticate_user(update, context, formatted_phone)
        return ConversationHandler.END

    async def _authenticate_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE, phone_number):
        """
        Core authentication logic that determines user type and shows appropriate interface.

        This enhanced version elegantly handles dual-role scenarios. When someone has multiple
        roles in the educational system (like being both an administrator and a teacher),
        they get to choose which role they want to use for their current session.

        Think of this like having different "work modes" - you can switch between being
        a system administrator managing users, or being a teacher managing your classes,
        but you focus on one role at a time for clarity and better user experience.
        """
        try:
            user_id = update.effective_user.id

            # Determine user type through our enhanced authentication system
            auth_result = await auth.get_user_type(user_id, phone_number, context.bot)

            # Store phone number for later use in workflows
            context.user_data['user_phone'] = phone_number

            # Remove the contact keyboard - we'll show appropriate interface next
            await update.message.reply_text(
                "✅ Telefon raqami qabul qilindi...",
                reply_markup=ReplyKeyboardRemove()
            )

            # Handle the authentication result
            if auth_result is None:
                # User not authorized - provide helpful guidance
                await update.message.reply_text(
                    f"{config.MESSAGES['auth_failed']}\n\n"
                    f"{config.MESSAGES['contact_support']}"
                )
                return

            # Check if this is a dual-role scenario
            if isinstance(auth_result, dict) and auth_result.get('type') == 'dual_role':
                # Store available roles and show selection interface
                context.user_data['available_roles'] = auth_result['available_roles']
                await self._show_role_selection(update, context, auth_result['available_roles'])
                return

            # Single role scenario - proceed directly to the appropriate interface
            await self._activate_role(update, context, auth_result)

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            await update.message.reply_text(config.MESSAGES['something_wrong'])

    async def _show_role_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE, available_roles):
        """
        Display role selection interface for users with multiple roles.

        This creates a clean, professional interface that allows users to choose
        which capacity they want to work in for this session. The design philosophy
        here is to make the choice clear and avoid confusion about current permissions.
        """
        # Create dynamic keyboard based on available roles
        keyboard = []

        role_descriptions = {
            'admin': ('👨‍💼 Admin sifatida kirish', 'Tizimni boshqarish va o\'qituvchilarni yaratish'),
            'teacher': ('👨‍🏫 O\'qituvchi sifatida kirish', 'Guruhlar va vazifalarni boshqarish'),
            'student': ('👨‍🎓 Talaba sifatida kirish', 'Vazifalarni bajarish va natijalarni ko\'rish')
        }

        for role in available_roles:
            if role in role_descriptions:
                button_text, description = role_descriptions[role]
                keyboard.append([KeyboardButton(button_text)])

        reply_markup = ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
            one_time_keyboard=True
        )

        # Create a welcoming message that explains the choice
        role_list = []
        for role in available_roles:
            if role in role_descriptions:
                _, description = role_descriptions[role]
                role_list.append(f"• {description}")

        message = (
                f"🎯 Sizda bir necha rol mavjud!\n\n"
                f"Quyidagi rollardan birini tanlang:\n" +
                "\n".join(role_list) +
                f"\n\nBu sessiya davomida tanlangan rol bilan ishlaysiz. "
                f"Keyin boshqa rolga o'tish mumkin."
        )

        await update.message.reply_text(message, reply_markup=reply_markup)

    async def _activate_role(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_type):
        """
        Activate the selected role and show the appropriate interface.

        This method centralizes the role activation logic, making it easy to
        handle both single-role users and dual-role users who have made their selection.
        """
        context.user_data['user_type'] = user_type

        # Route to appropriate interface based on user type
        if user_type == 'admin':
            await update.message.reply_text(config.MESSAGES['welcome_admin'])
            await admin_handlers.show_admin_menu(update, context)

        elif user_type == 'teacher':
            await update.message.reply_text(config.MESSAGES['welcome_teacher'])
            await teacher_handlers.show_teacher_menu(update, context)

        elif user_type == 'student':
            await update.message.reply_text(config.MESSAGES['welcome_student'])
            await student_handlers.show_student_menu(update, context)

    async def _handle_role_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Process role selection from users with multiple roles.

        This method converts the user's button selection back into a role type
        and activates the appropriate interface. It's designed to be intuitive
        and provide immediate feedback about the selected role.
        """
        selected_text = update.message.text.strip()
        available_roles = context.user_data.get('available_roles', [])

        # Map button text back to role types
        role_mapping = {
            config.BUTTONS['select_admin_role']: 'admin',
            config.BUTTONS['select_teacher_role']: 'teacher',
            config.BUTTONS['select_student_role']: 'student'
        }

        selected_role = role_mapping.get(selected_text)

        if selected_role and selected_role in available_roles:
            # Valid role selection - activate it
            await self._activate_role(update, context, selected_role)

            # Clear the role selection data since it's no longer needed
            context.user_data.pop('available_roles', None)
        else:
            # Invalid selection - ask them to try again
            await update.message.reply_text(
                "❌ Noto'g'ri tanlov. Iltimos, yuqoridagi tugmalardan birini bosing."
            )

    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle general text messages for menu navigation and context-aware routing.

        This enhanced version includes intelligent handling of role selection for dual-role users.
        The method acts as a traffic controller, examining the current context and user state
        to determine the most appropriate response to their message.
        """
        text = update.message.text.strip()
        user_type = context.user_data.get('user_type')

        try:
            # Priority 1: Handle role selection if user is in that state
            if 'available_roles' in context.user_data:
                await self._handle_role_selection(update, context)
                return

            # Priority 2: Main menu navigation buttons
            if text == config.COMMANDS['menu']:
                await self._show_main_menu(update, context, user_type)

            elif text == config.BUTTONS['back']:
                await self._handle_back_button(update, context, user_type)

            elif text == config.BUTTONS['back_to_groups']:
                await teacher_handlers.show_my_groups(update, context)

            # Priority 3: Role switching for dual-role users
            elif text == config.BUTTONS['switch_role']:
                await self._handle_role_switch(update, context)

            # Priority 4: Teacher group selection (dynamic text matching)
            elif user_type == 'teacher' and text.startswith('📚'):
                await teacher_handlers.select_group(update, context)

            # Priority 5: Handle unknown messages with helpful guidance
            else:
                await self._handle_unknown_message(update, context, user_type)

        except Exception as e:
            logger.error(f"Error handling text message: {e}")
            await update.message.reply_text(config.MESSAGES['something_wrong'])

    async def _handle_role_switch(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle role switching for dual-role users.

        This allows users who have multiple roles to switch between them without
        having to restart their session. This is particularly useful for administrators
        who also teach, as they might need to switch contexts frequently during their work.
        """
        # Check if user has the phone number stored (indicating they've been authenticated)
        user_phone = context.user_data.get('user_phone')
        if not user_phone:
            await update.message.reply_text(
                "❌ Avval telefon raqamingizni tasdiqlang. /start buyrug'ini yuboring."
            )
            return

        # Re-authenticate to get current role options
        try:
            user_id = update.effective_user.id
            auth_result = await auth.get_user_type(user_id, user_phone, context.bot)

            if isinstance(auth_result, dict) and auth_result.get('type') == 'dual_role':
                # Show role selection again
                context.user_data['available_roles'] = auth_result['available_roles']
                await self._show_role_selection(update, context, auth_result['available_roles'])
            else:
                # User only has one role now
                await update.message.reply_text(
                    "ℹ️ Sizda faqat bitta rol mavjud. Rol almashtirish kerak emas."
                )
        except Exception as e:
            logger.error(f"Error in role switch: {e}")
            await update.message.reply_text(config.MESSAGES['something_wrong'])

    async def handle_grade_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Special handler for numeric grade input during teacher grading workflow.
        This ensures grades are processed correctly in the grading context.
        """
        user_type = context.user_data.get('user_type')
        session = auth.get_user_session(update.effective_user.id)

        # Only process grades if user is teacher and in grading session
        if user_type == 'teacher' and session and session.get('session_type') == 'grading':
            await teacher_handlers.receive_grade(update, context)
        else:
            # Not in grading context, treat as regular message
            await self.handle_text_message(update, context)

    async def _show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_type):
        """Show the appropriate main menu based on user type"""
        if user_type == 'admin':
            await admin_handlers.show_admin_menu(update, context)
        elif user_type == 'teacher':
            await teacher_handlers.show_teacher_menu(update, context)
        elif user_type == 'student':
            await student_handlers.show_student_menu(update, context)
        else:
            await update.message.reply_text(config.MESSAGES['auth_failed'])

    async def _handle_back_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_type):
        """Handle back button navigation intelligently based on context"""
        session = auth.get_user_session(update.effective_user.id)

        if user_type == 'teacher' and session and session.get('selected_group_id'):
            # If teacher has a group selected, go back to group menu
            group = auth._get_group_by_id(session['selected_group_id'])
            if group:
                await teacher_handlers.show_group_management_menu(update, context, group)
            else:
                await teacher_handlers.show_teacher_menu(update, context)
        else:
            # Default back to main menu
            await self._show_main_menu(update, context, user_type)

    async def _handle_unknown_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_type):
        """Provide helpful guidance for unrecognized messages"""
        if not user_type:
            await update.message.reply_text(
                "❓ Avval /start buyrug'ini yuboring va telefon raqamingizni tasdiqqlang."
            )
        else:
            await update.message.reply_text(
                "❓ Noma'lum buyruq. Iltimos, tugmalardan foydalaning yoki /start buyrug'ini yuboring."
            )

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Global error handler for graceful error management.
        This ensures users always get helpful feedback even when things go wrong.
        """
        logger.error(f"Update {update} caused error {context.error}")

        # Try to send a user-friendly error message
        try:
            if update and update.message:
                await update.message.reply_text(
                    f"{config.MESSAGES['something_wrong']}\n\n"
                    f"Agar muammo davom etsa, /start buyrug'ini yuboring."
                )
        except Exception as e:
            logger.error(f"Error sending error message: {e}")

    def run(self):
        """
        Start the bot and begin processing messages.
        This is the main entry point that brings our educational system to life.
        """
        logger.info("🚀 Education Bot ishga tushmoqda...")

        # Initialize database if needed
        db.init_database()

        logger.info("📚 Ta'lim tizimi ishlamoqda!")

        # Start the bot with polling (good for development)
        self.app.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True  # Ignore messages sent while bot was offline
        )


def main():
    """
    Application entry point.
    This starts our complete education management system.
    """
    try:
        # Create and start the education bot
        bot = EducationBot()
        bot.run()

    except KeyboardInterrupt:
        logger.info("🛑 Bot to'xtatildi (Ctrl+C)")
    except Exception as e:
        logger.error(f"❌ Bot xatosi: {e}")
        raise


if __name__ == '__main__':
    main()