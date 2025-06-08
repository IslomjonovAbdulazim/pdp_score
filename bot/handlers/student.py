# bot/handlers/student.py
import logging
import json
from telegram import Update
from telegram.ext import ContextTypes
from bot.middlewares.auth import auth
from services.user_service import UserService
from services.assignment_service import AssignmentService
from services.grading_service import GradingService
from services.module_service import ModuleService
from bot.handlers.common import clear_conversation_state
from config import Config

logger = logging.getLogger(__name__)


async def submit_homework_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start homework submission process"""
    if not await auth.verify_student(update, context):
        return

    # Get student info
    student = UserService().get_user_by_telegram_id(update.effective_user.id)
    student_group_id = student['telegram_group_id']

    # Check for active assignment
    assignment_service = AssignmentService()
    active_assignment = assignment_service.get_active_assignment_for_student(student_group_id)

    if not active_assignment:
        await update.message.reply_text(
            "📝 **No Active Assignment**\n\n"
            "No homework is currently available for submission.\n"
            "Wait for your teacher to post a new assignment."
        )
        return

    # Check if already submitted
    if assignment_service.has_student_submitted(active_assignment['assignment_id'], student['user_id']):
        await update.message.reply_text(
            "✅ **Already Submitted**\n\n"
            f"You have already submitted homework for:\n"
            f"📝 {active_assignment['title']}\n\n"
            "Wait for your grade or contact teacher if needed."
        )
        return

    # Check deadline
    from datetime import datetime
    deadline = datetime.fromisoformat(active_assignment['deadline'])
    now = datetime.now()

    if now > deadline:
        # Calculate time since deadline
        time_diff = now - deadline

        # Check if still within late submission window
        assignment_service = AssignmentService()
        next_assignment = assignment_service.get_next_assignment_after(active_assignment['assignment_id'])

        if next_assignment:
            await update.message.reply_text(
                "❌ **Submission Closed**\n\n"
                f"Assignment: {active_assignment['title']}\n"
                "A new assignment has been posted.\n"
                "Late submissions are no longer accepted."
            )
            return
        else:
            # Still in late submission window
            penalty = int(Config.LATE_PENALTY_RATE * 100)
            await update.message.reply_text(
                f"⚠️ **Late Submission Warning**\n\n"
                f"Assignment: {active_assignment['title']}\n"
                f"Deadline was: {deadline.strftime('%Y-%m-%d %H:%M')}\n\n"
                f"Late penalty: -{penalty}% of earned score\n\n"
                "Continue with submission?"
            )

    # Start submission process
    context.user_data['conversation_state'] = 'student_submit'
    context.user_data['temp_data'] = {
        'assignment_id': active_assignment['assignment_id'],
        'files': [],
        'step': 'files'
    }

    await update.message.reply_text(
        f"📝 **Submit Homework**\n\n"
        f"**Assignment:** {active_assignment['title']}\n"
        f"**Deadline:** {active_assignment['deadline']}\n\n"
        f"Send up to {Config.MAX_FILE_UPLOADS} images/files.\n"
        "When finished, type `/done`"
    )


async def handle_done_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /done command for submission"""
    state = context.user_data.get('conversation_state')

    if state == 'student_submit':
        await handle_submission_done(update, context)
    else:
        await update.message.reply_text(
            "❌ `/done` command not expected here."
        )


async def handle_submission_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle file uploads for homework submission"""
    temp_data = context.user_data.get('temp_data', {})
    files = temp_data.get('files', [])

    # Check file limit
    if len(files) >= Config.MAX_FILE_UPLOADS:
        await update.message.reply_text(
            f"❌ Maximum {Config.MAX_FILE_UPLOADS} files allowed.\n"
            "Type `/done` to continue with explanation."
        )
        return

    # Get file ID
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        file_type = "Photo"
    elif update.message.document:
        file_id = update.message.document.file_id
        file_type = "Document"
    else:
        await update.message.reply_text("❌ Unsupported file type.")
        return

    files.append(file_id)
    temp_data['files'] = files

    remaining = Config.MAX_FILE_UPLOADS - len(files)

    await update.message.reply_text(
        f"📁 {file_type} added ({len(files)}/{Config.MAX_FILE_UPLOADS})\n\n"
        f"{'Send more files or ' if remaining > 0 else ''}Type `/done` to continue."
    )


async def handle_submission_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle completion of file upload for submission"""
    temp_data = context.user_data.get('temp_data', {})
    files = temp_data.get('files', [])

    if not files:
        await update.message.reply_text(
            "❌ No files uploaded. Please upload at least one file before using `/done`."
        )
        return

    temp_data['step'] = 'explanation'

    await update.message.reply_text(
        f"📝 **Files Collected ({len(files)})**\n\n"
        f"Now add your explanation (max {Config.MAX_EXPLANATION_LENGTH} words):"
    )


async def view_grades(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View student's grade history"""
    if not await auth.verify_student(update, context):
        return

    student = UserService().get_user_by_telegram_id(update.effective_user.id)
    grading_service = GradingService()

    # Get current active module
    module_service = ModuleService()
    active_module = module_service.get_student_active_module(student['user_id'])

    if not active_module:
        await update.message.reply_text(
            "📚 No active module found.\n\n"
            "Contact your teacher if this seems wrong."
        )
        return

    # Get grades for current module
    grades = grading_service.get_student_grades(student['user_id'], active_module['module_id'])

    if not grades:
        await update.message.reply_text(
            f"📊 **{active_module['module_name']} - No Grades Yet**\n\n"
            "No homework has been graded yet.\n"
            "Keep submitting your work! 📝"
        )
        return

    # Calculate total points
    total_points = sum(grade['final_score'] for grade in grades)

    message = f"📊 **{active_module['module_name']} - Your Grades**\n\n"
    message += f"🏆 **Total Points: {total_points:.1f}**\n\n"

    for i, grade in enumerate(grades, 1):
        penalty_text = ""
        if grade['late_penalty_applied'] > 0:
            penalty_text = f" (Late: -{int(grade['late_penalty_applied'] * 100)}%)"

        message += (
            f"**{i}. Assignment {grade['assignment_title'] or 'Homework'}**\n"
            f"📈 Score: {grade['final_score']:.1f}/{grade['max_points']}{penalty_text}\n"
            f"📅 Graded: {grade['graded_at'][:10]}\n"
        )

        if grade['teacher_feedback']:
            message += f"💬 Feedback: {grade['teacher_feedback']}\n"

        message += "\n"

    await update.message.reply_text(message, parse_mode='Markdown')


async def view_rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View student's current ranking"""
    if not await auth.verify_student(update, context):
        return

    student = UserService().get_user_by_telegram_id(update.effective_user.id)
    grading_service = GradingService()

    # Get student's ranking
    ranking_info = grading_service.get_student_ranking(student['user_id'])

    if not ranking_info:
        await update.message.reply_text(
            "📊 **No Ranking Available**\n\n"
            "No grades recorded yet or no active module."
        )
        return

    rank = ranking_info['rank']
    total_students = ranking_info['total_students']
    total_points = ranking_info['total_points']
    module_name = ranking_info['module_name']

    # Rank emoji
    if rank == 1:
        rank_emoji = "🥇"
    elif rank == 2:
        rank_emoji = "🥈"
    elif rank == 3:
        rank_emoji = "🥉"
    else:
        rank_emoji = f"#{rank}"

    # Performance message
    if rank <= 3:
        performance_msg = "🎉 Excellent work! Keep it up!"
    elif rank <= total_students // 2:
        performance_msg = "👍 Good progress! You're doing well!"
    else:
        performance_msg = "💪 Keep pushing! You can improve!"

    await update.message.reply_text(
        f"🏆 **Your Ranking - {module_name}**\n\n"
        f"{rank_emoji} **Position: {rank} out of {total_students}**\n"
        f"📊 **Total Points: {total_points:.1f}**\n\n"
        f"{performance_msg}",
        parse_mode='Markdown'
    )


async def view_modules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View available modules"""
    if not await auth.verify_student(update, context):
        return

    student = UserService().get_user_by_telegram_id(update.effective_user.id)
    module_service = ModuleService()

    # Get all modules for student's group
    modules = module_service.get_student_modules(student['user_id'])

    if not modules:
        await update.message.reply_text(
            "📚 **No Modules Found**\n\n"
            "Your class doesn't have any modules yet.\n"
            "Contact your teacher for more information."
        )
        return

    message = f"📚 **Your Modules ({len(modules)})**\n\n"

    for module in modules:
        status_emoji = "✅" if module['status'] == 'active' else "📋"
        status_text = "Active" if module['status'] == 'active' else "Completed"

        message += (
            f"{status_emoji} **{module['module_name']}**\n"
            f"📊 Status: {status_text}\n"
            f"📅 Started: {module['created_at'][:10]}\n"
        )

        if module['status'] == 'inactive' and module['ended_at']:
            message += f"🏁 Ended: {module['ended_at'][:10]}\n"

        message += "\n"

    await update.message.reply_text(message, parse_mode='Markdown')


async def last_grade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View last received grade"""
    if not await auth.verify_student(update, context):
        return

    student = UserService().get_user_by_telegram_id(update.effective_user.id)
    grading_service = GradingService()

    last_grade_info = grading_service.get_student_last_grade(student['user_id'])

    if not last_grade_info:
        await update.message.reply_text(
            "📊 **No Grades Yet**\n\n"
            "You haven't received any grades yet.\n"
            "Submit your homework to get started! 📝"
        )
        return

    grade = last_grade_info
    penalty_text = ""

    if grade['late_penalty_applied'] > 0:
        penalty_text = f"\n⚠️ Late penalty: -{int(grade['late_penalty_applied'] * 100)}%"

    await update.message.reply_text(
        f"📊 **Your Latest Grade**\n\n"
        f"📝 **Assignment:** {grade['assignment_title'] or 'Homework'}\n"
        f"📈 **Score:** {grade['final_score']:.1f}/{grade['max_points']}\n"
        f"📅 **Graded:** {grade['graded_at'][:10]}{penalty_text}\n\n"
        f"💬 **Feedback:**\n{grade['teacher_feedback'] or 'No feedback provided'}\n\n"
        f"🏆 **Your Total Points:** {grade['total_points']:.1f}",
        parse_mode='Markdown'
    )


async def handle_conversation_state(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle conversation states for student operations"""
    state = context.user_data.get('conversation_state')
    temp_data = context.user_data.get('temp_data', {})

    if state == 'student_submit':
        await handle_submit_conversation(update, context, temp_data)


async def handle_submit_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE, temp_data: dict):
    """Handle homework submission conversation"""
    step = temp_data.get('step')
    user_input = update.message.text.strip()

    if step == 'explanation':
        # Validate explanation length
        word_count = len(user_input.split())
        if word_count > Config.MAX_EXPLANATION_LENGTH:
            await update.message.reply_text(
                f"❌ Explanation too long ({word_count} words).\n"
                f"Maximum {Config.MAX_EXPLANATION_LENGTH} words allowed."
            )
            return

        if len(user_input) < 5:
            await update.message.reply_text(
                "❌ Explanation too short. Please provide more details."
            )
            return

        # Submit homework
        student = UserService().get_user_by_telegram_id(update.effective_user.id)
        assignment_service = AssignmentService()

        success = assignment_service.submit_homework(
            assignment_id=temp_data['assignment_id'],
            student_id=student['user_id'],
            explanation=user_input,
            file_ids=temp_data['files']
        )

        if success:
            # Get queue position
            grading_service = GradingService()
            queue_position = grading_service.get_student_queue_position(
                temp_data['assignment_id'],
                student['user_id']
            )

            await update.message.reply_text(
                f"✅ **Homework Submitted Successfully!**\n\n"
                f"📝 **Assignment ID:** #{success['submission_id']}\n"
                f"📁 **Files:** {len(temp_data['files'])}\n"
                f"📊 **Queue Position:** {queue_position}\n"
                f"⏰ **Submitted:** {success['submitted_at']}\n\n"
                "🎯 You will be notified when your homework is graded!\n"
                "Good luck! 🍀",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "❌ **Submission Failed**\n\n"
                "There was an error submitting your homework.\n"
                "Please try again or contact your teacher."
            )

        clear_conversation_state(context)