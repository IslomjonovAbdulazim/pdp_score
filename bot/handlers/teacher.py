# bot/handlers/teacher.py
import logging
import json
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.middlewares.auth import auth
from services.user_service import UserService
from services.group_service import GroupService
from services.module_service import ModuleService
from services.assignment_service import AssignmentService
from services.grading_service import GradingService
from bot.handlers.common import clear_conversation_state
from config import Config

logger = logging.getLogger(__name__)


# Module Management Commands
async def create_module(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create new module for current group"""
    if not await auth.verify_teacher(update, context):
        return

    teacher_id = UserService().get_user_by_telegram_id(update.effective_user.id)['user_id']
    current_group_id = context.user_data.get('current_group_id')

    if not current_group_id:
        await update.message.reply_text(
            "❌ No group selected. Use `/groups` to select a group first."
        )
        return

    module_service = ModuleService()

    # End current active module if exists
    current_module = module_service.get_active_module(current_group_id)
    if current_module:
        module_service.end_module(current_module['module_id'])

    # Create new module
    new_module = module_service.create_module(current_group_id)

    if new_module:
        await update.message.reply_text(
            f"✅ **{new_module['module_name']} Created!**\n\n"
            f"🏫 Group: {GroupService().get_group_by_id(current_group_id)['group_name']}\n"
            f"📅 Started: {new_module['created_at']}\n"
            f"📊 Status: Active\n\n"
            "All students start with 0 points in this new module.",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("❌ Failed to create module.")


async def end_module(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """End current active module"""
    if not await auth.verify_teacher(update, context):
        return

    current_group_id = context.user_data.get('current_group_id')
    if not current_group_id:
        await update.message.reply_text("❌ No group selected.")
        return

    module_service = ModuleService()
    active_module = module_service.get_active_module(current_group_id)

    if not active_module:
        await update.message.reply_text("❌ No active module to end.")
        return

    # Confirmation
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes, End Module", callback_data=f"confirm_end_module_{active_module['module_id']}"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_end_module")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"⚠️ **Confirm End Module**\n\n"
        f"Module: {active_module['module_name']}\n"
        f"This will make the group inactive.\n\n"
        "Are you sure?",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def current_module(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current active module info"""
    if not await auth.verify_teacher(update, context):
        return

    current_group_id = context.user_data.get('current_group_id')
    if not current_group_id:
        await update.message.reply_text("❌ No group selected.")
        return

    module_service = ModuleService()
    active_module = module_service.get_active_module(current_group_id)

    if not active_module:
        await update.message.reply_text(
            "📋 No active module.\n\n"
            "Use `/new_module` to create one."
        )
        return

    # Get student count and assignment info
    group_service = GroupService()
    assignment_service = AssignmentService()

    student_count = group_service.get_student_count(current_group_id)
    active_assignment = assignment_service.get_active_assignment(current_group_id)

    message = (
        f"📚 **Current Module**\n\n"
        f"**Name:** {active_module['module_name']}\n"
        f"**Started:** {active_module['created_at'][:10]}\n"
        f"**Students:** {student_count}\n"
        f"**Status:** ✅ Active\n\n"
    )

    if active_assignment:
        message += (
            f"**Active Assignment:**\n"
            f"📝 {active_assignment['title']}\n"
            f"⏰ Deadline: {active_assignment['deadline']}\n"
        )
    else:
        message += "**No active assignment**\n"

    await update.message.reply_text(message, parse_mode='Markdown')


# Group Management Commands
async def create_group_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start group creation process"""
    if not await auth.verify_teacher(update, context):
        return

    context.user_data['conversation_state'] = 'teacher_create_group'
    context.user_data['temp_data'] = {'step': 'name'}

    await update.message.reply_text(
        "🏫 **Create New Class Group**\n\n"
        "Enter the group name:\n"
        "Example: Advanced Mathematics Class"
    )


async def list_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List teacher's groups"""
    if not await auth.verify_teacher(update, context):
        return

    teacher_id = UserService().get_user_by_telegram_id(update.effective_user.id)['user_id']
    group_service = GroupService()
    groups = group_service.get_teacher_groups(teacher_id)

    if not groups:
        await update.message.reply_text(
            "📋 You have no groups yet.\n\n"
            "Use `/new_group` to create one."
        )
        return

    # Create inline keyboard
    keyboard = []
    for group in groups:
        keyboard.append([
            InlineKeyboardButton(
                f"🏫 {group['group_name']} ({'✅' if group['is_active'] else '❌'})",
                callback_data=f"group_{group['group_id']}"
            )
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)
    current_group_id = context.user_data.get('current_group_id')
    current_group_name = "None"

    if current_group_id:
        current_group = group_service.get_group_by_id(current_group_id)
        if current_group:
            current_group_name = current_group['group_name']

    await update.message.reply_text(
        f"🏫 **Your Groups ({len(groups)})**\n\n"
        f"**Current:** {current_group_name}\n\n"
        "Select a group to manage:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def select_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Select group by ID"""
    if not await auth.verify_teacher(update, context):
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            "❌ Please provide group ID.\n"
            "Usage: `/select_group 123`"
        )
        return

    try:
        group_id = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid group ID.")
        return

    teacher_id = UserService().get_user_by_telegram_id(update.effective_user.id)['user_id']
    group_service = GroupService()
    group = group_service.get_group_by_id(group_id)

    if not group or group['teacher_id'] != teacher_id:
        await update.message.reply_text("❌ Group not found or not yours.")
        return

    context.user_data['current_group_id'] = group_id

    await update.message.reply_text(
        f"✅ **Group Selected**\n\n"
        f"**Name:** {group['group_name']}\n"
        f"**Status:** {'✅ Active' if group['is_active'] else '❌ Inactive'}\n\n"
        "All commands will now target this group.",
        parse_mode='Markdown'
    )


async def current_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current selected group"""
    if not await auth.verify_teacher(update, context):
        return

    current_group_id = context.user_data.get('current_group_id')
    if not current_group_id:
        await update.message.reply_text(
            "❌ No group selected.\n\n"
            "Use `/groups` to select a group."
        )
        return

    group_service = GroupService()
    group = group_service.get_group_by_id(current_group_id)

    if not group:
        await update.message.reply_text("❌ Current group not found.")
        context.user_data.pop('current_group_id', None)
        return

    student_count = group_service.get_student_count(current_group_id)

    await update.message.reply_text(
        f"🏫 **Current Group**\n\n"
        f"**Name:** {group['group_name']}\n"
        f"**Students:** {student_count}\n"
        f"**Status:** {'✅ Active' if group['is_active'] else '❌ Inactive'}\n"
        f"**Created:** {group['created_at'][:10]}\n\n"
        "All commands target this group.",
        parse_mode='Markdown'
    )


# Assignment Management
async def create_assignment_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start assignment creation process"""
    if not await auth.verify_teacher(update, context):
        return

    current_group_id = context.user_data.get('current_group_id')
    if not current_group_id:
        await update.message.reply_text("❌ No group selected.")
        return

    # Check if group has active assignment
    assignment_service = AssignmentService()
    active_assignment = assignment_service.get_active_assignment(current_group_id)

    if active_assignment:
        # Show confirmation dialogs
        keyboard = [
            [
                InlineKeyboardButton("✅ Yes, Replace", callback_data="confirm_replace_assignment"),
                InlineKeyboardButton("❌ Cancel", callback_data="cancel_assignment")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"⚠️ **Active Assignment Exists**\n\n"
            f"Current: {active_assignment['title']}\n"
            f"Deadline: {active_assignment['deadline']}\n\n"
            "Creating new assignment will close the current one.\n"
            "Continue?",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return

    # Start assignment creation
    context.user_data['conversation_state'] = 'teacher_create_assignment'
    context.user_data['temp_data'] = {'files': [], 'step': 'files'}

    await update.message.reply_text(
        "📝 **Create New Assignment**\n\n"
        "Send images/files for the assignment.\n"
        "When finished, type `/done`"
    )


async def handle_done_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /done command for file uploads"""
    state = context.user_data.get('conversation_state')

    if state == 'teacher_create_assignment':
        await handle_assignment_done(update, context)
    else:
        await update.message.reply_text(
            "❌ `/done` command not expected here."
        )


async def handle_assignment_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle file uploads for assignment creation"""
    temp_data = context.user_data.get('temp_data', {})
    files = temp_data.get('files', [])

    # Get file ID
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
    elif update.message.document:
        file_id = update.message.document.file_id
    else:
        await update.message.reply_text("❌ Unsupported file type.")
        return

    files.append(file_id)
    temp_data['files'] = files

    await update.message.reply_text(
        f"📁 File added ({len(files)} total).\n"
        "Send more files or type `/done` to continue."
    )


async def handle_assignment_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle completion of file upload for assignment"""
    temp_data = context.user_data.get('temp_data', {})
    temp_data['step'] = 'title'

    await update.message.reply_text(
        "📝 Files collected.\n\n"
        "Now enter the assignment title:"
    )


# Grading Commands
async def grade_submission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Grade next submission in queue"""
    if not await auth.verify_teacher(update, context):
        return

    current_group_id = context.user_data.get('current_group_id')
    if not current_group_id:
        await update.message.reply_text("❌ No group selected.")
        return

    grading_service = GradingService()
    next_submission = grading_service.get_next_submission(current_group_id)

    if not next_submission:
        await update.message.reply_text(
            "✅ No submissions to grade!\n\n"
            "All caught up. 🎉"
        )
        return

    # Display submission for grading
    message = (
        f"📝 **Grade Submission**\n\n"
        f"**ID:** #{next_submission['submission_id']}\n"
        f"**Submitted:** {next_submission['submitted_at']}\n"
        f"**Explanation:**\n{next_submission['explanation']}\n\n"
        "Reply with: [score] [feedback]\n"
        "Example: 18 Great work! Check problem 3."
    )

    # Set grading state
    context.user_data['conversation_state'] = 'teacher_grading'
    context.user_data['temp_data'] = {'submission_id': next_submission['submission_id']}

    # Send files if any
    file_ids = json.loads(next_submission['telegram_file_ids']) if next_submission['telegram_file_ids'] else []

    if file_ids:
        await update.message.reply_text("📎 **Submission Files:**")
        for file_id in file_ids:
            try:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=file_id
                )
            except:
                pass

    await update.message.reply_text(message, parse_mode='Markdown')


async def check_queue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check grading queue status"""
    if not await auth.verify_teacher(update, context):
        return

    current_group_id = context.user_data.get('current_group_id')
    if not current_group_id:
        await update.message.reply_text("❌ No group selected.")
        return

    grading_service = GradingService()
    queue_count = grading_service.get_queue_count(current_group_id)

    await update.message.reply_text(
        f"📊 **Grading Queue**\n\n"
        f"Pending submissions: {queue_count}\n\n"
        f"{'✅ All caught up!' if queue_count == 0 else '📝 Use /grade to continue grading'}"
    )


# Conversation state handler
async def handle_conversation_state(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle conversation states for teacher operations"""
    state = context.user_data.get('conversation_state')
    temp_data = context.user_data.get('temp_data', {})

    if state == 'teacher_create_group':
        await handle_create_group_conversation(update, context, temp_data)
    elif state == 'teacher_create_assignment':
        await handle_create_assignment_conversation(update, context, temp_data)
    elif state == 'teacher_grading':
        await handle_grading_conversation(update, context, temp_data)


async def handle_create_group_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE, temp_data: dict):
    """Handle group creation conversation"""
    step = temp_data.get('step')
    user_input = update.message.text.strip()

    if step == 'name':
        if len(user_input) < 2:
            await update.message.reply_text("❌ Group name too short.")
            return

        temp_data['group_name'] = user_input
        temp_data['step'] = 'telegram_group_id'

        await update.message.reply_text(
            "📝 Group name saved.\n\n"
            "Now enter the Telegram group ID (negative number):\n"
            "Example: -1001234567890"
        )

    elif step == 'telegram_group_id':
        try:
            telegram_group_id = int(user_input)
            if telegram_group_id >= 0:
                await update.message.reply_text("❌ Group ID should be negative.")
                return
        except ValueError:
            await update.message.reply_text("❌ Invalid group ID.")
            return

        # Create group
        teacher_id = UserService().get_user_by_telegram_id(update.effective_user.id)['user_id']
        group_service = GroupService()

        new_group = group_service.create_group(
            group_name=temp_data['group_name'],
            teacher_id=teacher_id,
            telegram_group_id=telegram_group_id
        )

        if new_group:
            context.user_data['current_group_id'] = new_group['group_id']
            await update.message.reply_text(
                f"✅ **Group Created!**\n\n"
                f"**Name:** {new_group['group_name']}\n"
                f"**Group ID:** {telegram_group_id}\n\n"
                "Group set as current. Add students with `/add_student`",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ Failed to create group.")

        clear_conversation_state(context)


async def handle_grading_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE, temp_data: dict):
    """Handle grading conversation"""
    user_input = update.message.text.strip()
    submission_id = temp_data['submission_id']

    # Parse grade and feedback
    parts = user_input.split(' ', 1)

    try:
        score = float(parts[0])
        if score < 0 or score > Config.DEFAULT_MAX_POINTS:
            await update.message.reply_text(f"❌ Score must be between 0-{Config.DEFAULT_MAX_POINTS}")
            return
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Invalid format. Use: [score] [feedback]")
        return

    feedback = parts[1] if len(parts) > 1 else ""

    # Submit grade
    teacher_id = UserService().get_user_by_telegram_id(update.effective_user.id)['user_id']
    grading_service = GradingService()

    success = grading_service.submit_grade(
        submission_id=submission_id,
        teacher_id=teacher_id,
        points_earned=score,
        teacher_feedback=feedback
    )

    if success:
        queue_count = grading_service.get_queue_count(context.user_data.get('current_group_id'))

        keyboard = [
            [InlineKeyboardButton("➡️ Grade Next", callback_data="grade_next")],
            [InlineKeyboardButton("✅ Done", callback_data="grade_done")]
        ] if queue_count > 0 else []

        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

        message = (
            f"✅ **Grade Submitted!**\n\n"
            f"Score: {score}/{Config.DEFAULT_MAX_POINTS}\n"
            f"Student notified.\n\n"
        )

        if queue_count > 0:
            message += f"📊 Queue: {queue_count} remaining"
        else:
            message += "🎉 All submissions graded!"

        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("❌ Failed to submit grade.")

    clear_conversation_state(context)


# Additional helper functions for other commands would go here...
async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current module leaderboard"""
    if not await auth.verify_teacher(update, context):
        return

    current_group_id = context.user_data.get('current_group_id')
    if not current_group_id:
        await update.message.reply_text("❌ No group selected.")
        return

    grading_service = GradingService()
    leaderboard = grading_service.get_leaderboard(current_group_id)

    if not leaderboard:
        await update.message.reply_text("📊 No grades yet in current module.")
        return

    message = "🏆 **Module Leaderboard**\n\n"

    for i, student in enumerate(leaderboard, 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        message += f"{emoji} {student['full_name']}: {student['total_points']:.1f} pts\n"

    await update.message.reply_text(message, parse_mode='Markdown')


# Placeholder functions for other commands
async def start_module(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start new module (same as create_module)"""
    await create_module(update, context)


async def module_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show module history"""
    # Implementation here
    pass


async def list_students(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List students in current group"""
    # Implementation here
    pass


async def add_student_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start adding student"""
    # Implementation here
    pass


async def remove_student(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove student from group"""
    # Implementation here
    pass


async def update_grade_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start grade update process"""
    # Implementation here
    pass


async def pending_submissions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show pending submissions"""
    # Implementation here
    pass


async def handle_student_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle student selection callbacks"""
    # Implementation here
    pass


async def handle_group_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle group selection callbacks"""
    # Implementation here
    pass


async def handle_grade_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle grade action callbacks"""
    # Implementation here
    pass


async def handle_create_assignment_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE, temp_data: dict):
    """Handle assignment creation conversation"""
    # Implementation here
    pass