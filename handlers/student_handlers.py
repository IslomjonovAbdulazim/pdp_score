from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from database import db
from config import config
from auth import auth

# Conversation states for student interactions
WAITING_SUBMISSION_DESCRIPTION, WAITING_SUBMISSION_PHOTOS = range(2)


class StudentHandlers:
    """
    Handles all student-focused interactions in our education system.

    Students are the center of our educational ecosystem. Their experience should be:
    - Simple and intuitive (easy to understand what to do)
    - Encouraging and motivating (positive feedback and progress tracking)
    - Clear about expectations (what they need to submit and when)
    - Transparent about progress (current grades and standings)

    The student journey follows a natural learning cycle:
    1. Receive and understand tasks (current_task)
    2. Complete and submit work (submit_task)
    3. Receive feedback through grades
    4. Track progress and compare with peers (leaderboard)
    """

    @staticmethod
    async def show_student_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Display the main student learning dashboard.
        This is designed to be simple and focused on the core student activities.
        """
        keyboard = [
            [KeyboardButton(config.BUTTONS['current_task'])],
            [KeyboardButton(config.BUTTONS['my_progress'])],
            [KeyboardButton(config.BUTTONS['leaderboard'])]
        ]

        reply_markup = ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
            one_time_keyboard=False
        )

        await update.message.reply_text(
            "👨‍🎓 Talaba Paneli\n\n"
            "O'rganish jarayonini kuzatish uchun quyidagilardan birini tanlang:",
            reply_markup=reply_markup
        )

    @staticmethod
    async def show_current_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Display the current active task for the student's group.

        This is the primary learning interface where students understand what
        they need to accomplish. Clear task presentation is crucial for effective learning.
        """
        try:
            # Get student's group information
            student_phone = context.user_data.get('user_phone')
            student_group = auth.get_student_group(student_phone)

            if not student_group:
                await update.message.reply_text("❌ Guruh ma'lumotlari topilmadi.")
                return

            # Find the current active task for this group
            active_task = StudentHandlers._get_active_task(student_group['id'])

            if not active_task:
                # No active task - show encouragement and latest grade
                latest_grade = StudentHandlers._get_latest_grade(student_phone)
                if latest_grade:
                    await update.message.reply_text(
                        f"🎉 Hozirda faol vazifa yo'q!\n\n"
                        f"📊 Oxirgi bahoyingiz: {latest_grade['score']}/100\n"
                        f"📖 Modul: #{latest_grade['module_number']}\n\n"
                        f"Yangi vazifa tez orada beriladi. Sabr qiling! 💪"
                    )
                else:
                    await update.message.reply_text(config.MESSAGES['no_active_task'])
                return

            # Check if student has already submitted for this task
            student = auth._get_student_by_phone(student_phone)
            existing_submission = StudentHandlers._get_student_submission(active_task['id'], student['id'])

            if existing_submission:
                # Student has already submitted - show status
                if existing_submission['is_graded']:
                    # Show the grade
                    grade = StudentHandlers._get_submission_grade(existing_submission['id'])
                    await update.message.reply_text(
                        f"✅ Siz bu vazifani allaqachon topshirgansiz va baholangansiz!\n\n"
                        f"📊 Bahoyingiz: {grade['score']}/100\n"
                        f"📅 Topshirilgan: {existing_submission['submitted_at'][:16]}\n"
                        f"📅 Baholangan: {grade['graded_at'][:16] if grade else 'Nomalum'}"
                    )
                else:
                    # Show queue position
                    queue_position = StudentHandlers._get_queue_position(student['id'], student_group['id'])
                    await update.message.reply_text(
                        f"⏳ Sizning ishingiz tekshirilmoqda...\n\n"
                        f"📋 Vazifa: {active_task['description'][:100]}{'...' if len(active_task['description']) > 100 else ''}\n"
                        f"📅 Topshirilgan: {existing_submission['submitted_at'][:16]}\n\n"
                        f"{config.get_queue_position_text(queue_position)}\n"
                        f"O'qituvchi tez orada bahoyingizni qo'yadi."
                    )
            else:
                # Student hasn't submitted yet - show task and submit button
                await StudentHandlers._show_task_details(update, context, active_task)

        except Exception as e:
            print(f"Error showing current task: {e}")
            await update.message.reply_text(config.MESSAGES['something_wrong'])

    @staticmethod
    async def _show_task_details(update: Update, context: ContextTypes.DEFAULT_TYPE, task):
        """
        Display detailed task information with submission option.
        This presentation should inspire and guide students toward successful completion.
        """
        # Get module information for context
        module_info = db.execute_query(
            "SELECT module_number FROM modules WHERE id = ?",
            (task['module_id'],)
        )[0]

        # Build the task display message
        message = (
            f"📋 Joriy Vazifa\n"
            f"📖 Modul: #{module_info['module_number']}\n"
            f"📅 Berilgan: {task['created_at'][:16]}\n\n"
            f"📝 Vazifa tavsifi:\n{task['description']}\n\n"
            f"💡 Ishingizni topshirish uchun tugmani bosing!"
        )

        # Send task photos if available to provide visual context
        photos = config.json_to_photos(task['photos'])
        if photos:
            for photo_id in photos:
                await update.message.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=photo_id
                )

        # Create submit button
        keyboard = [[KeyboardButton(config.BUTTONS['submit_task'])]]
        reply_markup = ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
            one_time_keyboard=True
        )

        await update.message.reply_text(message, reply_markup=reply_markup)

    @staticmethod
    async def start_submit_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Begin the task submission process.
        This is a critical moment in the learning process where students
        demonstrate their understanding and effort.
        """
        try:
            student_phone = context.user_data.get('user_phone')
            student_group = auth.get_student_group(student_phone)
            active_task = StudentHandlers._get_active_task(student_group['id'])

            if not active_task:
                await update.message.reply_text(config.MESSAGES['no_active_task'])
                return ConversationHandler.END

            # Check if already submitted
            student = auth._get_student_by_phone(student_phone)
            existing_submission = StudentHandlers._get_student_submission(active_task['id'], student['id'])

            if existing_submission:
                await update.message.reply_text(config.MESSAGES['already_submitted'])
                return ConversationHandler.END

            # Store task info for the submission process
            context.user_data['submitting_task'] = active_task

            await update.message.reply_text(
                config.MESSAGES['submission_description'],
                reply_markup=StudentHandlers._get_cancel_keyboard()
            )

            return WAITING_SUBMISSION_DESCRIPTION

        except Exception as e:
            print(f"Error starting task submission: {e}")
            await update.message.reply_text(config.MESSAGES['something_wrong'])
            return ConversationHandler.END

    @staticmethod
    async def receive_submission_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Collect the student's description of their work.
        This text helps teachers understand the student's thought process and approach.
        """
        description = update.message.text.strip()

        if description == config.BUTTONS['cancel']:
            await StudentHandlers.cancel_operation(update, context)
            return ConversationHandler.END

        # Store description for later use
        context.user_data['submission_description'] = description

        await update.message.reply_text(
            config.MESSAGES['send_submission_photos'],
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton(config.BUTTONS['done'])],
                 [KeyboardButton(config.BUTTONS['cancel'])]],
                resize_keyboard=True, one_time_keyboard=True
            )
        )

        # Initialize photos list
        context.user_data['submission_photos'] = []

        return WAITING_SUBMISSION_PHOTOS

    @staticmethod
    async def receive_submission_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle photo submissions and finalize the submission.
        Visual evidence of work is often crucial for proper assessment.
        """
        try:
            photos = context.user_data.get('submission_photos', [])

            # Handle different message types
            if update.message.text:
                if update.message.text == config.BUTTONS['cancel']:
                    await StudentHandlers.cancel_operation(update, context)
                    return ConversationHandler.END
                elif update.message.text == config.BUTTONS['done']:
                    # Finalize submission
                    await StudentHandlers._finalize_submission(update, context)
                    return ConversationHandler.END
                else:
                    await update.message.reply_text(
                        "Faqat rasm yuboring yoki 'Tayyor' tugmasini bosing."
                    )
                    return WAITING_SUBMISSION_PHOTOS

            elif update.message.photo:
                # Add photo to collection
                photo_file_id = update.message.photo[-1].file_id  # Highest resolution
                photos.append(photo_file_id)
                context.user_data['submission_photos'] = photos

                if len(photos) >= config.MAX_PHOTOS_PER_SUBMISSION:
                    await update.message.reply_text(
                        f"📸 Maksimal rasm soni ({config.MAX_PHOTOS_PER_SUBMISSION}) qo'shildi. "
                        "'Tayyor' tugmasini bosing."
                    )
                else:
                    await update.message.reply_text(
                        f"📸 Rasm qabul qilindi ({len(photos)}/{config.MAX_PHOTOS_PER_SUBMISSION}). "
                        "Yana rasm yuborishingiz yoki 'Tayyor' tugmasini bosishingiz mumkin."
                    )

                return WAITING_SUBMISSION_PHOTOS

        except Exception as e:
            print(f"Error handling submission photos: {e}")
            await update.message.reply_text(config.MESSAGES['something_wrong'])
            return ConversationHandler.END

    @staticmethod
    async def _finalize_submission(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Save the complete submission to database.
        This marks a completed learning cycle for the student.
        """
        try:
            student_phone = context.user_data.get('user_phone')
            student = auth._get_student_by_phone(student_phone)

            task = context.user_data.get('submitting_task')
            description = context.user_data.get('submission_description')
            photos = context.user_data.get('submission_photos', [])

            # Create the submission record
            submission_id = db.execute_query(
                "INSERT INTO submissions (task_id, student_id, description, photos) VALUES (?, ?, ?, ?)",
                (task['id'], student['id'], description, config.photos_to_json(photos))
            )

            # Get queue position for feedback to student
            student_group = auth.get_student_group(student_phone)
            queue_position = StudentHandlers._get_queue_position(student['id'], student_group['id'])

            await update.message.reply_text(
                f"✅ Ishingiz muvaffaqiyatli topshirildi!\n\n"
                f"📋 Vazifa: {task['description'][:50]}{'...' if len(task['description']) > 50 else ''}\n"
                f"💬 Sizning izohi: {description[:50]}{'...' if len(description) > 50 else ''}\n"
                f"📸 Rasmlar soni: {len(photos)}\n\n"
                f"{config.get_queue_position_text(queue_position)}\n"
                f"O'qituvchi tez orada bahoyingizni qo'yadi. 📊"
            )

            # Clear submission data
            context.user_data.pop('submitting_task', None)
            context.user_data.pop('submission_description', None)
            context.user_data.pop('submission_photos', None)

        except Exception as e:
            print(f"Error finalizing submission: {e}")
            await update.message.reply_text(config.MESSAGES['something_wrong'])

    @staticmethod
    async def show_my_progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Display student's learning progress and achievements.
        Progress tracking is essential for motivation and self-assessment.
        """
        try:
            student_phone = context.user_data.get('user_phone')
            student = auth._get_student_by_phone(student_phone)
            student_group = auth.get_student_group(student_phone)

            if not student or not student_group:
                await update.message.reply_text("❌ Talaba ma'lumotlari topilmadi.")
                return

            # Get all grades for this student
            grades = db.execute_query(
                """SELECT g.*, m.module_number 
                   FROM grades g
                   JOIN modules m ON g.module_id = m.id
                   WHERE g.student_id = ?
                   ORDER BY m.module_number DESC""",
                (student['id'],)
            )

            if not grades:
                await update.message.reply_text(
                    f"📊 Sizning natijalaringiz\n\n"
                    f"👤 Ism: {student['fullname']}\n"
                    f"📚 Guruh: {student_group['name']}\n\n"
                    f"🔄 Hali hech qanday baho yo'q.\n"
                    f"Birinchi vazifangizni topshiring!"
                )
                return

            # Calculate statistics
            latest_grade = grades[0]  # Most recent module
            total_score = sum(grade['score'] for grade in grades)
            average_score = total_score / len(grades)
            highest_score = max(grade['score'] for grade in grades)

            # Build progress message
            message = (
                f"📊 Sizning natijalaringiz\n\n"
                f"👤 Ism: {student['fullname']}\n"
                f"📚 Guruh: {student_group['name']}\n\n"
                f"📈 Umumiy statistika:\n"
                f"• Eng so'nggi baho: {latest_grade['score']}/100 (Modul #{latest_grade['module_number']})\n"
                f"• O'rtacha baho: {average_score:.1f}/100\n"
                f"• Eng yuqori baho: {highest_score}/100\n"
                f"• Jami baholangan modullar: {len(grades)}\n\n"
                f"📋 Modullar bo'yicha tarix:\n"
            )

            # Show each module's grade
            for grade in grades:
                grade_emoji = StudentHandlers._get_grade_emoji(grade['score'])
                message += f"• Modul #{grade['module_number']}: {grade['score']}/100 {grade_emoji}\n"

            await update.message.reply_text(message)

        except Exception as e:
            print(f"Error showing student progress: {e}")
            await update.message.reply_text(config.MESSAGES['something_wrong'])

    @staticmethod
    async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Display group leaderboard to encourage healthy competition.
        Social comparison can be a powerful motivator when done positively.
        """
        try:
            student_phone = context.user_data.get('user_phone')
            student = auth._get_student_by_phone(student_phone)
            student_group = auth.get_student_group(student_phone)

            # Get latest module number for this group
            latest_module = db.execute_query(
                "SELECT MAX(module_number) as max_num FROM modules WHERE group_id = ?",
                (student_group['id'],)
            )[0]

            if not latest_module['max_num']:
                await update.message.reply_text("📊 Hali hech qanday modul yaratilmagan.")
                return

            current_module_num = latest_module['max_num']

            # Get leaderboard for current module
            leaderboard = db.execute_query(
                """SELECT s.fullname, g.score, g.graded_at
                   FROM grades g
                   JOIN students s ON g.student_id = s.id
                   JOIN modules m ON g.module_id = m.id
                   WHERE m.group_id = ? AND m.module_number = ?
                   ORDER BY g.score DESC, g.graded_at ASC""",
                (student_group['id'], current_module_num)
            )

            if not leaderboard:
                await update.message.reply_text(
                    f"📊 Reytinglar jadval\n"
                    f"📖 Modul #{current_module_num}\n\n"
                    f"Hali hech kim baholanmagan."
                )
                return

            # Build leaderboard message
            message = (
                f"🏆 Guruh reytinglari\n"
                f"📚 Guruh: {student_group['name']}\n"
                f"📖 Modul: #{current_module_num}\n\n"
            )

            # Find current student's position
            current_student_position = None
            for i, entry in enumerate(leaderboard, 1):
                if entry['fullname'] == student['fullname']:
                    current_student_position = i
                    break

            # Show top performers and current student
            for i, entry in enumerate(leaderboard[:10], 1):  # Top 10
                position_emoji = StudentHandlers._get_position_emoji(i)
                grade_emoji = StudentHandlers._get_grade_emoji(entry['score'])

                # Highlight current student
                if entry['fullname'] == student['fullname']:
                    message += f"➤ {position_emoji} {entry['fullname']}: {entry['score']}/100 {grade_emoji} (Siz)\n"
                else:
                    message += f"{position_emoji} {entry['fullname']}: {entry['score']}/100 {grade_emoji}\n"

            # If current student is not in top 10, show their position
            if current_student_position and current_student_position > 10:
                message += f"\n...\n➤ {current_student_position}. {student['fullname']}: {leaderboard[current_student_position - 1]['score']}/100 (Siz)\n"

            # Add motivational message
            if current_student_position == 1:
                message += "\n🎉 Tabriklaymiz! Siz birinchi o'rindasiz!"
            elif current_student_position and current_student_position <= 3:
                message += "\n💪 Ajoyib! Siz eng yaxshilar qatorida!"
            else:
                message += "\n📈 Davom eting! Har doim yaxshilanish mumkin!"

            await update.message.reply_text(message)

        except Exception as e:
            print(f"Error showing leaderboard: {e}")
            await update.message.reply_text(config.MESSAGES['something_wrong'])

    # Helper methods for student operations
    @staticmethod
    def _get_active_task(group_id):
        """Get the currently active task for a group"""
        try:
            tasks = db.execute_query(
                """SELECT t.* FROM tasks t
                   JOIN modules m ON t.module_id = m.id
                   WHERE m.group_id = ? AND t.is_active = TRUE
                   ORDER BY t.created_at DESC LIMIT 1""",
                (group_id,)
            )
            return tasks[0] if tasks else None
        except:
            return None

    @staticmethod
    def _get_student_submission(task_id, student_id):
        """Check if student has submitted for a specific task"""
        try:
            submissions = db.execute_query(
                "SELECT * FROM submissions WHERE task_id = ? AND student_id = ?",
                (task_id, student_id)
            )
            return submissions[0] if submissions else None
        except:
            return None

    @staticmethod
    def _get_submission_grade(submission_id):
        """Get grade for a specific submission"""
        try:
            grades = db.execute_query(
                "SELECT * FROM grades WHERE submission_id = ?",
                (submission_id,)
            )
            return grades[0] if grades else None
        except:
            return None

    @staticmethod
    def _get_queue_position(student_id, group_id):
        """Calculate student's position in grading queue"""
        try:
            # Get all ungraded submissions for this group, ordered by submission time
            ungraded = db.execute_query(
                """SELECT s.student_id FROM submissions s
                   JOIN tasks t ON s.task_id = t.id
                   JOIN modules m ON t.module_id = m.id
                   WHERE m.group_id = ? AND s.is_graded = FALSE
                   ORDER BY s.submitted_at ASC""",
                (group_id,)
            )

            for i, submission in enumerate(ungraded, 1):
                if submission['student_id'] == student_id:
                    return i
            return 0
        except:
            return 0

    @staticmethod
    def _get_latest_grade(student_phone):
        """Get student's most recent grade with module info"""
        try:
            student = auth._get_student_by_phone(student_phone)
            if not student:
                return None

            grades = db.execute_query(
                """SELECT g.score, m.module_number
                   FROM grades g
                   JOIN modules m ON g.module_id = m.id
                   WHERE g.student_id = ?
                   ORDER BY g.graded_at DESC LIMIT 1""",
                (student['id'],)
            )
            return grades[0] if grades else None
        except:
            return None

    @staticmethod
    def _get_grade_emoji(score):
        """Get appropriate emoji for grade score"""
        if score >= 90:
            return "🌟"
        elif score >= 80:
            return "⭐"
        elif score >= 70:
            return "✅"
        elif score >= 60:
            return "👍"
        else:
            return "📈"

    @staticmethod
    def _get_position_emoji(position):
        """Get emoji for leaderboard position"""
        if position == 1:
            return "🥇"
        elif position == 2:
            return "🥈"
        elif position == 3:
            return "🥉"
        else:
            return f"{position}."

    @staticmethod
    async def cancel_operation(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel current operation and return to student menu"""
        context.user_data.pop('submitting_task', None)
        context.user_data.pop('submission_description', None)
        context.user_data.pop('submission_photos', None)

        await update.message.reply_text("❌ Amal bekor qilindi.")
        await StudentHandlers.show_student_menu(update, context)

    @staticmethod
    def _get_cancel_keyboard():
        """Helper method to create a cancel-only keyboard"""
        return ReplyKeyboardMarkup(
            [[KeyboardButton(config.BUTTONS['cancel'])]],
            resize_keyboard=True,
            one_time_keyboard=True
        )


# Create global instance for easy import
student_handlers = StudentHandlers()