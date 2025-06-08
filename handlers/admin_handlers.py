from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from database import db
from config import config

# Conversation states for admin operations
WAITING_TEACHER_NAME, WAITING_TEACHER_PHONE, CONFIRMING_DELETE = range(3)


class AdminHandlers:
    """
    Handles all admin-specific operations.
    Admins can create, view, and delete teachers.
    This is the management layer of the education system.
    """

    @staticmethod
    async def show_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Display the main admin menu with available actions.
        This is the control center for administrators.
        """
        keyboard = [
            [KeyboardButton(config.BUTTONS['create_teacher'])],
            [KeyboardButton(config.BUTTONS['view_teachers'])],
            [KeyboardButton(config.BUTTONS['delete_teacher'])]
        ]

        reply_markup = ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
            one_time_keyboard=False
        )

        await update.message.reply_text(
            "👨‍💼 Admin Panel\n\n"
            "O'qituvchilarni boshqarish uchun quyidagi tugmalardan birini tanlang:",
            reply_markup=reply_markup
        )

    @staticmethod
    async def start_create_teacher(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Begin the teacher creation process.
        This starts a conversation to collect teacher information.
        """
        await update.message.reply_text(
            config.MESSAGES['enter_teacher_name'],
            reply_markup=AdminHandlers._get_cancel_keyboard()
        )
        return WAITING_TEACHER_NAME

    @staticmethod
    async def receive_teacher_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Store teacher name and ask for phone number.
        We validate the name here to ensure it's not empty.
        """
        teacher_name = update.message.text.strip()

        if not teacher_name or teacher_name == config.BUTTONS['cancel']:
            await AdminHandlers.cancel_operation(update, context)
            return ConversationHandler.END

        # Store teacher name in context for later use
        context.user_data['teacher_name'] = teacher_name

        await update.message.reply_text(
            config.MESSAGES['enter_teacher_phone'],
            reply_markup=AdminHandlers._get_cancel_keyboard()
        )
        return WAITING_TEACHER_PHONE

    @staticmethod
    async def receive_teacher_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Store teacher phone and create the teacher account.
        This completes the teacher creation process with validation.
        """
        teacher_phone = update.message.text.strip()

        if teacher_phone == config.BUTTONS['cancel']:
            await AdminHandlers.cancel_operation(update, context)
            return ConversationHandler.END

        # Format and validate phone number
        formatted_phone = config.format_phone(teacher_phone)
        teacher_name = context.user_data.get('teacher_name')

        try:
            # Check if teacher with this phone already exists
            existing_teacher = db.execute_query(
                "SELECT id FROM teachers WHERE phone_number = ?",
                (formatted_phone,)
            )

            if existing_teacher:
                await update.message.reply_text(
                    f"❌ Bu telefon raqami bilan o'qituvchi allaqachon mavjud!\n"
                    f"Telefon: {formatted_phone}"
                )
            else:
                # Create new teacher
                teacher_id = db.execute_query(
                    "INSERT INTO teachers (fullname, phone_number) VALUES (?, ?)",
                    (teacher_name, formatted_phone)
                )

                await update.message.reply_text(
                    f"✅ O'qituvchi muvaffaqiyatli yaratildi!\n\n"
                    f"👤 Ism: {teacher_name}\n"
                    f"📱 Telefon: {formatted_phone}\n"
                    f"🆔 ID: {teacher_id}"
                )

                # Clear context data
                context.user_data.clear()

        except Exception as e:
            print(f"Error creating teacher: {e}")
            await update.message.reply_text(config.MESSAGES['something_wrong'])

        # Return to admin menu
        await AdminHandlers.show_admin_menu(update, context)
        return ConversationHandler.END

    @staticmethod
    async def view_all_teachers(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Display all teachers in the system.
        Shows their basic info and creation dates for admin oversight.
        """
        try:
            teachers = db.execute_query(
                "SELECT * FROM teachers ORDER BY created_at DESC"
            )

            if not teachers:
                await update.message.reply_text(
                    "📝 Hali hech qanday o'qituvchi ro'yxatdan o'tmagan.\n"
                    "Yangi o'qituvchi qo'shish uchun tegishli tugmani bosing."
                )
            else:
                # Build a formatted list of all teachers
                message = "👥 Barcha o'qituvchilar ro'yxati:\n\n"

                for i, teacher in enumerate(teachers, 1):
                    # Format creation date for better readability
                    created_date = teacher['created_at'][:10]  # Get just the date part

                    message += (
                        f"{i}. 👤 {teacher['fullname']}\n"
                        f"   📱 {teacher['phone_number']}\n"
                        f"   📅 Qo'shilgan: {created_date}\n"
                        f"   🆔 ID: {teacher['id']}\n\n"
                    )

                # If message is too long, split it
                if len(message) > 4000:
                    # Send in chunks to avoid Telegram's message length limit
                    for i in range(0, len(message), 4000):
                        await update.message.reply_text(message[i:i + 4000])
                else:
                    await update.message.reply_text(message)

        except Exception as e:
            print(f"Error viewing teachers: {e}")
            await update.message.reply_text(config.MESSAGES['something_wrong'])

    @staticmethod
    async def start_delete_teacher(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Show list of teachers for deletion selection.
        This provides a safe way to remove teachers from the system.
        """
        try:
            teachers = db.execute_query(
                "SELECT * FROM teachers ORDER BY fullname"
            )

            if not teachers:
                await update.message.reply_text(
                    "📝 O'chirish uchun hech qanday o'qituvchi yo'q."
                )
                return ConversationHandler.END

            # Create buttons for each teacher
            keyboard = []
            for teacher in teachers:
                button_text = f"{teacher['fullname']} ({teacher['phone_number']})"
                keyboard.append([KeyboardButton(button_text)])

            # Add cancel button
            keyboard.append([KeyboardButton(config.BUTTONS['cancel'])])

            reply_markup = ReplyKeyboardMarkup(
                keyboard,
                resize_keyboard=True,
                one_time_keyboard=True
            )

            # Store teachers data for later reference
            context.user_data['teachers_list'] = teachers

            await update.message.reply_text(
                "⚠️ O'chirish uchun o'qituvchini tanlang:\n\n"
                "Diqqat: O'qituvchini o'chirish uning barcha guruh va ma'lumotlarini ham o'chiradi!",
                reply_markup=reply_markup
            )

            return CONFIRMING_DELETE

        except Exception as e:
            print(f"Error starting teacher deletion: {e}")
            await update.message.reply_text(config.MESSAGES['something_wrong'])
            return ConversationHandler.END

    @staticmethod
    async def confirm_delete_teacher(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle teacher deletion confirmation and execution.
        This removes the teacher and all associated data (groups, modules, etc.).
        """
        selected_text = update.message.text.strip()

        if selected_text == config.BUTTONS['cancel']:
            await AdminHandlers.cancel_operation(update, context)
            return ConversationHandler.END

        try:
            teachers_list = context.user_data.get('teachers_list', [])
            selected_teacher = None

            # Find the selected teacher by matching the button text format
            for teacher in teachers_list:
                button_text = f"{teacher['fullname']} ({teacher['phone_number']})"
                if button_text == selected_text:
                    selected_teacher = teacher
                    break

            if not selected_teacher:
                await update.message.reply_text(
                    "❌ Noto'g'ri tanlov. Qaytadan urinib ko'ring."
                )
                return CONFIRMING_DELETE

            # Delete teacher (CASCADE will handle related data)
            db.execute_query(
                "DELETE FROM teachers WHERE id = ?",
                (selected_teacher['id'],)
            )

            await update.message.reply_text(
                f"✅ O'qituvchi muvaffaqiyatli o'chirildi!\n\n"
                f"👤 {selected_teacher['fullname']}\n"
                f"📱 {selected_teacher['phone_number']}\n\n"
                f"⚠️ Bu o'qituvchining barcha guruh va ma'lumotlari ham o'chirildi."
            )

            # Clear context data
            context.user_data.clear()

        except Exception as e:
            print(f"Error deleting teacher: {e}")
            await update.message.reply_text(config.MESSAGES['something_wrong'])

        # Return to admin menu
        await AdminHandlers.show_admin_menu(update, context)
        return ConversationHandler.END

    @staticmethod
    async def cancel_operation(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Cancel any ongoing admin operation and return to menu.
        This provides a safe exit from any admin conversation.
        """
        context.user_data.clear()
        await update.message.reply_text("❌ Amal bekor qilindi.")
        await AdminHandlers.show_admin_menu(update, context)

    @staticmethod
    def _get_cancel_keyboard():
        """Helper method to create a cancel-only keyboard"""
        return ReplyKeyboardMarkup(
            [[KeyboardButton(config.BUTTONS['cancel'])]],
            resize_keyboard=True,
            one_time_keyboard=True
        )


# Create global instance for easy import
admin_handlers = AdminHandlers()