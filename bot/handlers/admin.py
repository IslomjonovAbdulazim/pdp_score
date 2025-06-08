# bot/handlers/admin.py
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.middlewares.auth import auth
from services.user_service import UserService
from services.group_service import GroupService
from bot.handlers.common import clear_conversation_state

logger = logging.getLogger(__name__)


async def list_teachers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all teachers with action buttons"""
    if not await auth.verify_admin(update, context):
        return

    user_service = UserService()
    teachers = user_service.get_all_teachers()

    if not teachers:
        await update.message.reply_text("📋 No teachers found in the system.")
        return

    # Create inline keyboard with teacher options
    keyboard = []
    for teacher in teachers:
        keyboard.append([
            InlineKeyboardButton(
                f"👩‍🏫 {teacher['full_name']} ({teacher['phone_number']})",
                callback_data=f"teacher_{teacher['user_id']}"
            )
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"👥 **Teachers ({len(teachers)})**\n\n"
        "Select a teacher to manage:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def handle_teacher_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle teacher selection from inline keyboard"""
    query = update.callback_query
    await query.answer()

    teacher_id = int(query.data.split('_')[1])
    user_service = UserService()
    teacher = user_service.get_user_by_id(teacher_id)

    if not teacher:
        await query.edit_message_text("❌ Teacher not found.")
        return

    # Create action buttons
    keyboard = [
        [
            InlineKeyboardButton("✏️ Edit", callback_data=f"edit_teacher_{teacher_id}"),
            InlineKeyboardButton("🗑️ Delete", callback_data=f"delete_teacher_{teacher_id}")
        ],
        [InlineKeyboardButton("⬅️ Back", callback_data="back_to_teachers")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"👩‍🏫 **Teacher Details**\n\n"
        f"**Name:** {teacher['full_name']}\n"
        f"**Phone:** {teacher['phone_number']}\n"
        f"**Group ID:** {teacher['telegram_group_id']}\n"
        f"**Created:** {teacher['created_at']}\n"
        f"**Status:** {'✅ Active' if teacher['is_active'] else '❌ Inactive'}\n\n"
        "Choose an action:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def handle_teacher_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle teacher edit/delete actions"""
    query = update.callback_query
    await query.answer()

    action, teacher_id = query.data.split('_')[1], int(query.data.split('_')[2])

    if action == "delete":
        # Confirmation for delete
        keyboard = [
            [
                InlineKeyboardButton("✅ Yes, Delete", callback_data=f"confirm_delete_{teacher_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"teacher_{teacher_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "⚠️ **Confirm Deletion**\n\n"
            "Are you sure you want to delete this teacher?\n"
            "This action cannot be undone.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    elif action == "edit":
        # Start edit conversation
        context.user_data['conversation_state'] = 'admin_edit_teacher'
        context.user_data['temp_data'] = {'teacher_id': teacher_id, 'edit_field': 'phone'}

        await query.edit_message_text(
            "✏️ **Edit Teacher**\n\n"
            "Enter new phone number:"
        )


async def create_teacher_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start teacher creation process"""
    if not await auth.verify_admin(update, context):
        return

    context.user_data['conversation_state'] = 'admin_create_teacher'
    context.user_data['temp_data'] = {'step': 'phone'}

    await update.message.reply_text(
        "👩‍🏫 **Create New Teacher**\n\n"
        "Please enter the teacher's phone number (with country code):\n"
        "Example: +998901234567"
    )


async def system_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show system statistics"""
    if not await auth.verify_admin(update, context):
        return

    user_service = UserService()
    group_service = GroupService()

    # Get statistics
    stats = {
        'total_admins': len(user_service.get_users_by_role('admin')),
        'total_teachers': len(user_service.get_users_by_role('teacher')),
        'total_students': len(user_service.get_users_by_role('student')),
        'total_groups': len(group_service.get_all_groups()),
        'active_groups': len(group_service.get_active_groups())
    }

    await update.message.reply_text(
        f"📊 **System Statistics**\n\n"
        f"👨‍💼 Administrators: {stats['total_admins']}\n"
        f"👩‍🏫 Teachers: {stats['total_teachers']}\n"
        f"👨‍🎓 Students: {stats['total_students']}\n"
        f"🏫 Total Groups: {stats['total_groups']}\n"
        f"✅ Active Groups: {stats['active_groups']}\n\n"
        f"🔗 Total Users: {stats['total_admins'] + stats['total_teachers'] + stats['total_students']}",
        parse_mode='Markdown'
    )


async def list_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all groups in the system"""
    if not await auth.verify_admin(update, context):
        return

    group_service = GroupService()
    groups = group_service.get_all_groups_with_teachers()

    if not groups:
        await update.message.reply_text("📋 No groups found in the system.")
        return

    message = f"🏫 **All Groups ({len(groups)})**\n\n"

    for group in groups:
        status = "✅ Active" if group['is_active'] else "❌ Inactive"
        message += (
            f"**{group['group_name']}**\n"
            f"👩‍🏫 Teacher: {group['teacher_name']}\n"
            f"📊 Status: {status}\n"
            f"🆔 Group ID: {group['telegram_group_id']}\n"
            f"📅 Created: {group['created_at'][:10]}\n\n"
        )

    await update.message.reply_text(message, parse_mode='Markdown')


async def handle_conversation_state(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle conversation state for admin operations"""
    state = context.user_data.get('conversation_state')
    temp_data = context.user_data.get('temp_data', {})

    if state == 'admin_create_teacher':
        await handle_create_teacher_conversation(update, context, temp_data)
    elif state == 'admin_edit_teacher':
        await handle_edit_teacher_conversation(update, context, temp_data)


async def handle_create_teacher_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE, temp_data: dict):
    """Handle teacher creation conversation"""
    step = temp_data.get('step')
    user_input = update.message.text.strip()

    if step == 'phone':
        # Validate phone number
        if not user_input.startswith('+') or len(user_input) < 10:
            await update.message.reply_text(
                "❌ Invalid phone number format. Please include country code.\n"
                "Example: +998901234567"
            )
            return

        temp_data['phone_number'] = user_input
        temp_data['step'] = 'fullname'

        await update.message.reply_text(
            "📝 Phone number saved.\n\n"
            "Now enter the teacher's full name:"
        )

    elif step == 'fullname':
        if len(user_input) < 2:
            await update.message.reply_text("❌ Name too short. Please enter full name:")
            return

        temp_data['full_name'] = user_input
        temp_data['step'] = 'group_id'

        await update.message.reply_text(
            "👤 Name saved.\n\n"
            "Now enter the teacher group ID (negative number):\n"
            "Example: -1001234567890"
        )

    elif step == 'group_id':
        try:
            group_id = int(user_input)
            if group_id >= 0:
                await update.message.reply_text(
                    "❌ Group ID should be negative. Example: -1001234567890"
                )
                return
        except ValueError:
            await update.message.reply_text("❌ Invalid group ID. Please enter a number.")
            return

        # Create teacher account
        user_service = UserService()
        success = user_service.create_teacher(
            phone_number=temp_data['phone_number'],
            full_name=temp_data['full_name'],
            telegram_group_id=group_id
        )

        if success:
            await update.message.reply_text(
                f"✅ **Teacher Created Successfully!**\n\n"
                f"**Name:** {temp_data['full_name']}\n"
                f"**Phone:** {temp_data['phone_number']}\n"
                f"**Group ID:** {group_id}\n\n"
                "The teacher can now use the bot.",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "❌ Failed to create teacher. Phone number might already exist."
            )

        clear_conversation_state(context)


async def handle_edit_teacher_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE, temp_data: dict):
    """Handle teacher editing conversation"""
    # Implementation for editing teacher details
    # This would follow similar pattern to create_teacher
    pass