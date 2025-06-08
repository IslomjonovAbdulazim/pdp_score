from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from database import db
from config import config
from auth import auth
import json

# Conversation states for teacher operations - each represents a different input stage
WAITING_GROUP_NAME, WAITING_CHANNEL_ID, WAITING_STUDENT_NAME, WAITING_STUDENT_PHONE = range(4)
WAITING_TASK_DESCRIPTION, WAITING_TASK_PHOTOS, WAITING_GRADE = range(4, 7)


class TeacherHandlers:
    """
    Handles all teacher-specific operations in our education system.
    Teachers are the heart of the learning process - they create the structure
    (groups and modules), assign work (tasks), and evaluate progress (grading).

    The workflow follows educational best practices:
    1. Organize students into learning groups
    2. Break learning into digestible modules
    3. Assign tasks within each module
    4. Provide timely feedback through grading
    """

    @staticmethod
    async def show_teacher_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Display the main teacher control panel.
        This is where teachers choose their primary educational activities.
        """
        # Clear any existing session when returning to main menu
        auth.clear_user_session(update.effective_user.id)

        keyboard = [
            [KeyboardButton(config.BUTTONS['my_groups'])],
            [KeyboardButton(config.BUTTONS['create_group'])],
        ]

        reply_markup = ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
            one_time_keyboard=False
        )

        await update.message.reply_text(
            "👨‍🏫 O'qituvchi Paneli\n\n"
            "Ta'lim jarayonini boshqarish uchun quyidagi tanlovlardan birini bajaring:",
            reply_markup=reply_markup
        )

    @staticmethod
    async def show_my_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Display all groups belonging to this teacher.
        Groups are the fundamental organizational unit in our education system.
        Each group represents a class of students learning together.
        """
        try:
            # Get teacher's phone from Telegram contact info (this should be stored in context)
            teacher_phone = context.user_data.get('user_phone')
            if not teacher_phone:
                await update.message.reply_text("❌ Telefon raqami topilmadi. Qaytadan /start bosing.")
                return

            # Retrieve all groups created by this teacher
            groups = auth.get_teacher_groups(teacher_phone)

            if not groups:
                await update.message.reply_text(
                    "📝 Siz hali hech qanday guruh yaratmagansiz.\n"
                    "Yangi guruh yaratish uchun tegishli tugmani bosing."
                )
                return

            # Create interactive buttons for each group
            keyboard = []
            for group in groups:
                # Show group name with student count for quick overview
                student_count = TeacherHandlers._get_group_student_count(group['id'])
                button_text = f"📚 {group['name']} ({student_count} talaba)"
                keyboard.append([KeyboardButton(button_text)])

            # Add navigation button
            keyboard.append([KeyboardButton(config.BUTTONS['back'])])

            reply_markup = ReplyKeyboardMarkup(
                keyboard,
                resize_keyboard=True,
                one_time_keyboard=True
            )

            # Store groups data for when user selects one
            context.user_data['teacher_groups'] = groups

            await update.message.reply_text(
                "📚 Sizning guruhlaringiz:\n\n"
                "Boshqarish uchun guruhni tanlang:",
                reply_markup=reply_markup
            )

        except Exception as e:
            print(f"Error showing teacher groups: {e}")
            await update.message.reply_text(config.MESSAGES['something_wrong'])

    @staticmethod
    async def select_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle group selection and show group management options.
        Once a teacher selects a group, they can perform all group-specific operations.
        This is where the educational workflow branches into specific activities.
        """
        selected_text = update.message.text.strip()

        if selected_text == config.BUTTONS['back']:
            await TeacherHandlers.show_teacher_menu(update, context)
            return

        try:
            # Find the selected group by matching the button text format
            groups = context.user_data.get('teacher_groups', [])
            selected_group = None

            for group in groups:
                student_count = TeacherHandlers._get_group_student_count(group['id'])
                button_text = f"📚 {group['name']} ({student_count} talaba)"
                if button_text == selected_text:
                    selected_group = group
                    break

            if not selected_group:
                await update.message.reply_text("❌ Noto'g'ri tanlov. Qaytadan urinib ko'ring.")
                return

            # Set user session to track which group they're working with
            auth.set_user_session(update.effective_user.id, selected_group['id'])

            # Show group management menu
            await TeacherHandlers.show_group_management_menu(update, context, selected_group)

        except Exception as e:
            print(f"Error selecting group: {e}")
            await update.message.reply_text(config.MESSAGES['something_wrong'])

    @staticmethod
    async def show_group_management_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, group):
        """
        Display all available actions for the selected group.
        This menu represents the core educational activities teachers perform.
        """
        # Get current module info for context
        current_module = TeacherHandlers._get_current_module(group['id'])

        keyboard = [
            [KeyboardButton(config.BUTTONS['create_module'])],
            [KeyboardButton(config.BUTTONS['create_task'])],
            [KeyboardButton(config.BUTTONS['grade_submissions'])],
            [KeyboardButton(config.BUTTONS['add_student'])],
            [KeyboardButton(config.BUTTONS['remove_student'])],
            [KeyboardButton(config.BUTTONS['back_to_groups'])]
        ]

        reply_markup = ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
            one_time_keyboard=False
        )

        # Show group status with educational context
        module_info = ""
        if current_module:
            module_info = f"\n📖 Joriy modul: #{current_module['module_number']}"

        student_count = TeacherHandlers._get_group_student_count(group['id'])

        await update.message.reply_text(
            f"📚 Guruh: {group['name']}\n"
            f"👥 Talabalar soni: {student_count}{module_info}\n\n"
            "Quyidagi amallardan birini tanlang:",
            reply_markup=reply_markup
        )

    @staticmethod
    async def create_new_module(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Create a new learning module for the selected group.
        Modules represent distinct learning phases - think of them as chapters
        in a textbook or units in a curriculum. Each module has its own tasks and grades.
        """
        try:
            # Get current session to know which group we're working with
            session = auth.get_user_session(update.effective_user.id)
            if not session:
                await update.message.reply_text("❌ Guruh tanlanmagan. Qaytadan boshlang.")
                return

            group_id = session['selected_group_id']

            # Calculate next module number (auto-increment within group)
            last_module = db.execute_query(
                "SELECT MAX(module_number) as max_num FROM modules WHERE group_id = ?",
                (group_id,)
            )

            next_module_number = 1
            if last_module and last_module[0]['max_num']:
                next_module_number = last_module[0]['max_num'] + 1

            # Create the new module
            module_id = db.execute_query(
                "INSERT INTO modules (group_id, module_number) VALUES (?, ?)",
                (group_id, next_module_number)
            )

            await update.message.reply_text(
                f"✅ Yangi modul yaratildi!\n\n"
                f"📖 Modul raqami: #{next_module_number}\n"
                f"🆔 Modul ID: {module_id}\n\n"
                "Endi bu modul uchun vazifalar yaratishingiz mumkin."
            )

        except Exception as e:
            print(f"Error creating module: {e}")
            await update.message.reply_text(config.MESSAGES['something_wrong'])

    @staticmethod
    async def start_create_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Begin task creation process.
        Tasks are the actual learning activities students complete.
        Each task belongs to a module and represents specific learning objectives.
        """
        try:
            session = auth.get_user_session(update.effective_user.id)
            if not session:
                await update.message.reply_text("❌ Guruh tanlanmagan.")
                return

            # Check if we have a current module
            current_module = TeacherHandlers._get_current_module(session['selected_group_id'])
            if not current_module:
                await update.message.reply_text(
                    "❌ Avval modul yaratish kerak!\n"
                    "Vazifa yaratish uchun kamida bitta modul bo'lishi shart."
                )
                return

            await update.message.reply_text(
                f"📋 Vazifa yaratish\n"
                f"📖 Modul: #{current_module['module_number']}\n\n"
                f"{config.MESSAGES['enter_task_description']}",
                reply_markup=TeacherHandlers._get_cancel_keyboard()
            )

            return WAITING_TASK_DESCRIPTION

        except Exception as e:
            print(f"Error starting task creation: {e}")
            await update.message.reply_text(config.MESSAGES['something_wrong'])
            return ConversationHandler.END

    @staticmethod
    async def receive_task_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Store task description and optionally request photos.
        Task descriptions should clearly communicate learning objectives to students.
        """
        description = update.message.text.strip()

        if description == config.BUTTONS['cancel']:
            await TeacherHandlers.cancel_operation(update, context)
            return ConversationHandler.END

        # Store description for later use
        context.user_data['task_description'] = description

        # Ask for photos (optional)
        await update.message.reply_text(
            f"{config.MESSAGES['send_task_photos']}\n\n"
            "Rasm yubormasangiz, 'Tayyor' tugmasini bosing.",
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton(config.BUTTONS['done'])],
                 [KeyboardButton(config.BUTTONS['cancel'])]],
                resize_keyboard=True, one_time_keyboard=True
            )
        )

        return WAITING_TASK_PHOTOS

    @staticmethod
    async def receive_task_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle task photos and create the final task.
        Photos help provide visual context and clarity for task instructions.
        """
        try:
            session = auth.get_user_session(update.effective_user.id)
            current_module = TeacherHandlers._get_current_module(session['selected_group_id'])

            task_description = context.user_data.get('task_description')
            photos = []

            # Handle different message types
            if update.message.text:
                if update.message.text == config.BUTTONS['cancel']:
                    await TeacherHandlers.cancel_operation(update, context)
                    return ConversationHandler.END
                elif update.message.text != config.BUTTONS['done']:
                    await update.message.reply_text("Faqat rasm yuboring yoki 'Tayyor' tugmasini bosing.")
                    return WAITING_TASK_PHOTOS
            elif update.message.photo:
                # Store photo file_id
                photo_file_id = update.message.photo[-1].file_id  # Get highest resolution
                photos.append(photo_file_id)

                await update.message.reply_text(
                    "📸 Rasm qabul qilindi. Yana rasm yuborishingiz yoki 'Tayyor' tugmasini bosishingiz mumkin."
                )
                return WAITING_TASK_PHOTOS

            # Deactivate any existing active tasks for this group (only one active task per group)
            db.execute_query(
                """UPDATE tasks SET is_active = FALSE 
                   WHERE module_id IN (SELECT id FROM modules WHERE group_id = ?)""",
                (session['selected_group_id'],)
            )

            # Create the new task
            task_id = db.execute_query(
                "INSERT INTO tasks (module_id, description, photos, is_active) VALUES (?, ?, ?, ?)",
                (current_module['id'], task_description, config.photos_to_json(photos), True)
            )

            # Send notification to group channel
            await TeacherHandlers._notify_group_channel(update, context, session['selected_group_id'], task_description,
                                                        photos)

            await update.message.reply_text(
                f"✅ Vazifa muvaffaqiyatli yaratildi va guruhlarga yuborildi!\n\n"
                f"📋 Vazifa: {task_description[:100]}{'...' if len(task_description) > 100 else ''}\n"
                f"📖 Modul: #{current_module['module_number']}\n"
                f"🆔 Vazifa ID: {task_id}"
            )

            context.user_data.clear()
            return ConversationHandler.END

        except Exception as e:
            print(f"Error creating task: {e}")
            await update.message.reply_text(config.MESSAGES['something_wrong'])
            return ConversationHandler.END

    @staticmethod
    async def start_grading(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Begin the grading workflow.
        Grading is a critical educational process where teachers provide feedback
        and assessment to guide student learning and progress.
        """
        try:
            session = auth.get_user_session(update.effective_user.id)
            if not session:
                await update.message.reply_text("❌ Guruh tanlanmagan.")
                return

            # Get ungraded submissions for this group
            ungraded_submissions = TeacherHandlers._get_ungraded_submissions(session['selected_group_id'])

            if not ungraded_submissions:
                await update.message.reply_text(
                    "✅ Barcha ishlar baholangan yoki hali hech kim ish topshirmagan.\n"
                    "Yangi topshiriqlar kelganda xabar beramiz."
                )
                return

            # Set grading session
            auth.set_user_session(update.effective_user.id, session['selected_group_id'], 'grading')

            # Show first submission
            await TeacherHandlers._show_next_submission(update, context, ungraded_submissions)

        except Exception as e:
            print(f"Error starting grading: {e}")
            await update.message.reply_text(config.MESSAGES['something_wrong'])

    @staticmethod
    async def _show_next_submission(update: Update, context: ContextTypes.DEFAULT_TYPE, submissions_queue):
        """
        Display the next submission in the grading queue.
        This creates an efficient workflow for teachers to review student work systematically.
        """
        if not submissions_queue:
            await update.message.reply_text("✅ Barcha ishlar baholandi!")
            auth.clear_user_session(update.effective_user.id)
            await TeacherHandlers.show_teacher_menu(update, context)
            return

        current_submission = submissions_queue[0]
        remaining_count = len(submissions_queue) - 1

        # Get student and task info for context
        student_info = db.execute_query(
            "SELECT fullname FROM students WHERE id = ?",
            (current_submission['student_id'],)
        )[0]

        task_info = db.execute_query(
            "SELECT description FROM tasks WHERE id = ?",
            (current_submission['task_id'],)
        )[0]

        # Store current submission data
        context.user_data['current_submission'] = current_submission
        context.user_data['remaining_submissions'] = submissions_queue[1:]

        # Format submission message
        message = (
            f"📝 Baholash navbati\n\n"
            f"👤 Talaba: {student_info['fullname']}\n"
            f"📋 Vazifa: {task_info['description'][:100]}{'...' if len(task_info['description']) > 100 else ''}\n"
            f"📅 Topshirilgan: {current_submission['submitted_at'][:16]}\n\n"
        )

        if current_submission['description']:
            message += f"💬 Talaba izohi: {current_submission['description']}\n\n"

        message += f"⏳ Qolgan ishlar: {remaining_count}\n\n"
        message += "Bahoni 0-100 orasida kiriting:"

        # Send submission photos if available
        photos = config.json_to_photos(current_submission['photos'])
        if photos:
            for photo_id in photos:
                await update.message.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=photo_id
                )

        await update.message.reply_text(
            message,
            reply_markup=TeacherHandlers._get_grading_keyboard(remaining_count)
        )

    @staticmethod
    async def _get_ungraded_submissions(group_id):
        """Get all ungraded submissions for a specific group, ordered by submission time"""
        return db.execute_query(
            """SELECT s.* FROM submissions s
               JOIN tasks t ON s.task_id = t.id
               JOIN modules m ON t.module_id = m.id
               WHERE m.group_id = ? AND s.is_graded = FALSE
               ORDER BY s.submitted_at ASC""",
            (group_id,)
        )

    @staticmethod
    def _get_group_student_count(group_id):
        """Helper to get the number of students in a group"""
        try:
            result = db.execute_query(
                "SELECT COUNT(*) as count FROM students WHERE group_id = ?",
                (group_id,)
            )
            return result[0]['count'] if result else 0
        except:
            return 0

    @staticmethod
    def _get_current_module(group_id):
        """Get the most recent module for a group"""
        try:
            modules = db.execute_query(
                "SELECT * FROM modules WHERE group_id = ? ORDER BY module_number DESC LIMIT 1",
                (group_id,)
            )
            return modules[0] if modules else None
        except:
            return None

    @staticmethod
    async def _notify_group_channel(update: Update, context: ContextTypes.DEFAULT_TYPE, group_id, description, photos):
        """Send task notification to the group's Telegram channel"""
        try:
            group = db.execute_query("SELECT * FROM groups WHERE id = ?", (group_id,))[0]
            channel_id = group['channel_id']

            message = f"📋 Yangi vazifa!\n\n{description}"

            # Send photos first if available
            if photos:
                for photo_id in photos:
                    await update.message.bot.send_photo(
                        chat_id=channel_id,
                        photo=photo_id
                    )

            # Send text message
            await update.message.bot.send_message(
                chat_id=channel_id,
                text=message
            )
        except Exception as e:
            print(f"Error notifying group channel: {e}")

    @staticmethod
    async def cancel_operation(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel current operation and return to appropriate menu"""
        context.user_data.clear()
        await update.message.reply_text("❌ Amal bekor qilindi.")
        await TeacherHandlers.show_teacher_menu(update, context)

    @staticmethod
    def _get_cancel_keyboard():
        """Helper method to create a cancel-only keyboard"""
        return ReplyKeyboardMarkup(
            [[KeyboardButton(config.BUTTONS['cancel'])]],
            resize_keyboard=True,
            one_time_keyboard=True
        )

    @staticmethod
    async def receive_grade(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Process the grade input and save it to the database.
        This completes the feedback loop in our educational system.
        """
        try:
            grade_text = update.message.text.strip()

            # Handle special commands during grading
            if "Keyingi ish" in grade_text:
                remaining_submissions = context.user_data.get('remaining_submissions', [])
                await TeacherHandlers._show_next_submission(update, context, remaining_submissions)
                return
            elif grade_text == "⏸ Keyinroq baholash":
                auth.clear_user_session(update.effective_user.id)
                await update.message.reply_text("✅ Baholash to'xtatildi. Keyinroq davom etishingiz mumkin.")
                await TeacherHandlers.show_teacher_menu(update, context)
                return

            # Validate grade input
            try:
                grade = int(grade_text)
                if grade < 0 or grade > 100:
                    await update.message.reply_text("❌ Baho 0 dan 100 gacha bo'lishi kerak. Qaytadan kiriting:")
                    return
            except ValueError:
                await update.message.reply_text("❌ Faqat raqam kiriting (0-100). Qaytadan urinib ko'ring:")
                return

            # Get current submission data
            current_submission = context.user_data.get('current_submission')
            if not current_submission:
                await update.message.reply_text("❌ Xatolik yuz berdi. Qaytadan boshlang.")
                return

            # Get module info for this submission
            module_info = db.execute_query(
                "SELECT m.* FROM modules m JOIN tasks t ON m.id = t.module_id WHERE t.id = ?",
                (current_submission['task_id'],)
            )[0]

            # Save the grade
            db.execute_query(
                "INSERT INTO grades (submission_id, module_id, student_id, score) VALUES (?, ?, ?, ?)",
                (current_submission['id'], module_info['id'], current_submission['student_id'], grade)
            )

            # Mark submission as graded
            db.execute_query(
                "UPDATE submissions SET is_graded = TRUE WHERE id = ?",
                (current_submission['id'],)
            )

            # Get student info for confirmation message
            student_info = db.execute_query(
                "SELECT fullname FROM students WHERE id = ?",
                (current_submission['student_id'],)
            )[0]

            await update.message.reply_text(
                f"✅ Baho saqlandi!\n\n"
                f"👤 Talaba: {student_info['fullname']}\n"
                f"📊 Baho: {grade}/100\n"
                f"📖 Modul: #{module_info['module_number']}"
            )

            # Continue with next submission
            remaining_submissions = context.user_data.get('remaining_submissions', [])
            await TeacherHandlers._show_next_submission(update, context, remaining_submissions)

        except Exception as e:
            print(f"Error processing grade: {e}")
            await update.message.reply_text(config.MESSAGES['something_wrong'])

    @staticmethod
    async def start_create_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Begin group creation process"""
        await update.message.reply_text(
            config.MESSAGES['enter_group_name'],
            reply_markup=TeacherHandlers._get_cancel_keyboard()
        )
        return WAITING_GROUP_NAME

    @staticmethod
    async def receive_group_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Store group name and ask for channel ID"""
        group_name = update.message.text.strip()

        if group_name == config.BUTTONS['cancel']:
            await TeacherHandlers.cancel_operation(update, context)
            return ConversationHandler.END

        context.user_data['group_name'] = group_name

        await update.message.reply_text(
            config.MESSAGES['enter_channel_id'],
            reply_markup=TeacherHandlers._get_cancel_keyboard()
        )
        return WAITING_CHANNEL_ID

    @staticmethod
    async def receive_channel_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Create the group with provided information"""
        try:
            channel_id = update.message.text.strip()

            if channel_id == config.BUTTONS['cancel']:
                await TeacherHandlers.cancel_operation(update, context)
                return ConversationHandler.END

            group_name = context.user_data.get('group_name')
            teacher_phone = context.user_data.get('user_phone')

            # Get teacher ID
            teacher = auth._get_teacher_by_phone(teacher_phone)
            if not teacher:
                await update.message.reply_text("❌ O'qituvchi ma'lumotlari topilmadi.")
                return ConversationHandler.END

            # Create the group
            group_id = db.execute_query(
                "INSERT INTO groups (name, channel_id, teacher_id) VALUES (?, ?, ?)",
                (group_name, channel_id, teacher['id'])
            )

            await update.message.reply_text(
                f"✅ Guruh muvaffaqiyatli yaratildi!\n\n"
                f"📚 Nom: {group_name}\n"
                f"🆔 Kanal ID: {channel_id}\n"
                f"🔢 Guruh ID: {group_id}"
            )

            context.user_data.clear()
            await TeacherHandlers.show_teacher_menu(update, context)
            return ConversationHandler.END

        except Exception as e:
            print(f"Error creating group: {e}")
            await update.message.reply_text(config.MESSAGES['something_wrong'])
            return ConversationHandler.END

    @staticmethod
    async def start_add_student(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Begin student addition process"""
        session = auth.get_user_session(update.effective_user.id)
        if not session:
            await update.message.reply_text("❌ Guruh tanlanmagan.")
            return ConversationHandler.END

        await update.message.reply_text(
            config.MESSAGES['enter_student_name'],
            reply_markup=TeacherHandlers._get_cancel_keyboard()
        )
        return WAITING_STUDENT_NAME

    @staticmethod
    async def receive_student_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Store student name and ask for phone"""
        student_name = update.message.text.strip()

        if student_name == config.BUTTONS['cancel']:
            await TeacherHandlers.cancel_operation(update, context)
            return ConversationHandler.END

        context.user_data['student_name'] = student_name

        await update.message.reply_text(
            config.MESSAGES['enter_student_phone'],
            reply_markup=TeacherHandlers._get_cancel_keyboard()
        )
        return WAITING_STUDENT_PHONE

    @staticmethod
    async def receive_student_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Add student to the selected group"""
        try:
            student_phone = update.message.text.strip()

            if student_phone == config.BUTTONS['cancel']:
                await TeacherHandlers.cancel_operation(update, context)
                return ConversationHandler.END

            session = auth.get_user_session(update.effective_user.id)
            student_name = context.user_data.get('student_name')
            formatted_phone = config.format_phone(student_phone)

            # Check if student already exists in this group
            existing_student = db.execute_query(
                "SELECT id FROM students WHERE phone_number = ? AND group_id = ?",
                (formatted_phone, session['selected_group_id'])
            )

            if existing_student:
                await update.message.reply_text("❌ Bu talaba allaqachon guruhda mavjud!")
            else:
                # Add student to group
                student_id = db.execute_query(
                    "INSERT INTO students (fullname, phone_number, group_id) VALUES (?, ?, ?)",
                    (student_name, formatted_phone, session['selected_group_id'])
                )

                await update.message.reply_text(
                    f"✅ Talaba guruhga qo'shildi!\n\n"
                    f"👤 Ism: {student_name}\n"
                    f"📱 Telefon: {formatted_phone}\n"
                    f"🆔 ID: {student_id}"
                )

            context.user_data.clear()
            return ConversationHandler.END

        except Exception as e:
            print(f"Error adding student: {e}")
            await update.message.reply_text(config.MESSAGES['something_wrong'])
            return ConversationHandler.END

    @staticmethod
    def _get_grading_keyboard(remaining_count):
        """Create keyboard for grading workflow"""
        keyboard = []
        if remaining_count > 0:
            keyboard.append([KeyboardButton(f"📊 Keyingi ish ({remaining_count} qoldi)")])
        keyboard.append([KeyboardButton("⏸ Keyinroq baholash")])

        return ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
            one_time_keyboard=True
        )


# Create global instance for easy import
teacher_handlers = TeacherHandlers()