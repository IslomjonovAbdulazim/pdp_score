from database import db
from config import config
from telegram import ChatMember
from telegram.constants import ChatMemberStatus
import asyncio


class AuthSystem:
    """
    Comprehensive authentication and permission management system for educational institutions.

    This system handles the complex authentication requirements of educational environments
    where individuals often serve multiple roles and permissions need to be verified
    in real-time against current organizational membership. The design supports:

    - Multi-role authentication (admin, teacher, student)
    - Real-time permission verification via Telegram API
    - Session management for complex educational workflows
    - Graceful handling of permission changes and role transitions
    """

    @staticmethod
    async def get_user_type(user_id, phone_number, bot):
        """
        Determine user type based on phone number and group membership verification.

        This method implements a comprehensive authentication strategy that goes beyond
        simple database lookups. It verifies current organizational membership through
        Telegram's API, ensuring that permissions reflect real-time institutional
        relationships rather than potentially stale database records.

        The dual-role detection feature specifically addresses the reality of educational
        institutions where administrators often teach classes and teachers may have
        administrative responsibilities. Rather than forcing users to maintain separate
        accounts, the system allows them to choose their current working context.

        Args:
            user_id: Telegram user ID for API verification calls
            phone_number: User's phone number for database lookups
            bot: Telegram bot instance for making API calls

        Returns:
            - Single role string ('admin', 'teacher', 'student') for single-role users
            - Dictionary with multiple roles for users with dual permissions
            - None if user has no valid roles
        """
        formatted_phone = config.format_phone(phone_number)

        # Initialize role detection flags
        is_admin = config.is_admin(formatted_phone)
        is_teacher = False
        is_student = False

        # Verify teacher status through database record and group membership
        teacher_data = AuthSystem._get_teacher_by_phone(formatted_phone)
        if teacher_data:
            # Real-time verification ensures only current faculty members have access
            is_in_teachers_group = await AuthSystem._check_group_membership(
                bot, user_id, config.TEACHERS_GROUP_ID
            )
            if is_in_teachers_group:
                is_teacher = True

        # Verify student status through database record and channel membership
        student_data = AuthSystem._get_student_by_phone(formatted_phone)
        if student_data:
            # Students must be active members of their learning group's channel
            group_data = AuthSystem._get_group_by_id(student_data['group_id'])
            if group_data:
                is_in_channel = await AuthSystem._check_channel_membership(
                    bot, user_id, group_data['channel_id']
                )
                if is_in_channel:
                    is_student = True

        # Determine authentication result based on detected roles
        role_count = sum([is_admin, is_teacher, is_student])

        if role_count == 0:
            # No valid roles detected - user lacks institutional access
            return None
        elif role_count == 1:
            # Single role scenario - proceed directly to appropriate interface
            if is_admin:
                AuthSystem._ensure_admin_exists(formatted_phone)
                return 'admin'
            elif is_teacher:
                return 'teacher'
            elif is_student:
                return 'student'
        else:
            # Multiple roles detected - enable role selection interface
            available_roles = []
            if is_admin:
                AuthSystem._ensure_admin_exists(formatted_phone)
                available_roles.append('admin')
            if is_teacher:
                available_roles.append('teacher')
            if is_student:
                available_roles.append('student')

            return {'type': 'dual_role', 'available_roles': available_roles}

        return None

    @staticmethod
    def _ensure_admin_exists(phone_number):
        """
        Ensure admin record exists in database for system integrity.

        This method maintains consistency between configuration-based admin
        identification and database records. It automatically creates admin
        records when they don't exist, ensuring that all system users have
        proper database representation for audit and tracking purposes.
        """
        try:
            existing_admin = db.execute_query(
                "SELECT id FROM admins WHERE phone_number = ?",
                (phone_number,)
            )
            if not existing_admin:
                db.execute_query(
                    "INSERT INTO admins (phone_number) VALUES (?)",
                    (phone_number,)
                )
                print(f"Admin record created for {phone_number}")
        except Exception as e:
            print(f"Error ensuring admin exists: {e}")

    @staticmethod
    def _get_teacher_by_phone(phone_number):
        """
        Retrieve teacher record by phone number with error resilience.

        This method provides the foundation for teacher authentication by
        connecting phone numbers to institutional teacher records. The error
        handling ensures that authentication continues to function even if
        database issues occur during the lookup process.
        """
        try:
            teachers = db.execute_query(
                "SELECT * FROM teachers WHERE phone_number = ?",
                (phone_number,)
            )
            return teachers[0] if teachers else None
        except Exception as e:
            print(f"Error retrieving teacher record: {e}")
            return None

    @staticmethod
    def _get_student_by_phone(phone_number):
        """
        Retrieve student record by phone number with graceful error handling.

        Student authentication relies on accurate database lookups that connect
        phone numbers to learning group memberships. This method ensures that
        temporary database issues don't prevent legitimate students from
        accessing their educational resources.
        """
        try:
            students = db.execute_query(
                "SELECT * FROM students WHERE phone_number = ?",
                (phone_number,)
            )
            return students[0] if students else None
        except Exception as e:
            print(f"Error retrieving student record: {e}")
            return None

    @staticmethod
    def _get_group_by_id(group_id):
        """
        Retrieve learning group information by ID for context verification.

        Learning groups form the organizational backbone of the educational
        system, connecting students to their appropriate learning contexts.
        This method provides the group details needed for channel membership
        verification and educational workflow management.
        """
        try:
            groups = db.execute_query(
                "SELECT * FROM groups WHERE id = ?",
                (group_id,)
            )
            return groups[0] if groups else None
        except Exception as e:
            print(f"Error retrieving group information: {e}")
            return None

    @staticmethod
    async def _check_group_membership(bot, user_id, group_id):
        """
        Verify active membership in Telegram groups for real-time permission validation.

        This method implements real-time verification that ensures only current
        institutional members can access educational features. By checking actual
        Telegram group membership rather than relying solely on database records,
        the system automatically adapts to organizational changes such as staff
        departures or role transitions.

        The verification process queries Telegram's servers directly, providing
        immediate feedback about current membership status. This approach prevents
        the security gaps that could arise from relying on potentially outdated
        local records.

        Args:
            bot: Telegram bot instance for API calls
            user_id: Telegram user ID to verify
            group_id: Telegram group ID to check membership against

        Returns:
            Boolean indicating whether user is an active group member
        """
        try:
            member = await bot.get_chat_member(chat_id=group_id, user_id=user_id)

            # Verify active membership status using current API constants
            return member.status in [
                ChatMemberStatus.OWNER,  # Group owner (highest privilege)
                ChatMemberStatus.ADMINISTRATOR,  # Group administrator
                ChatMemberStatus.MEMBER  # Regular group member
            ]
        except Exception as e:
            print(f"Error verifying group membership: {e}")
            # Fail securely - deny access if verification cannot be completed
            return False

    @staticmethod
    async def _check_channel_membership(bot, user_id, channel_id):
        """
        Verify active membership in Telegram channels for student access control.

        Channel membership verification ensures that students can only access
        educational content and features for learning groups where they are
        active participants. This creates natural boundaries around educational
        interactions and ensures that course-specific content remains properly
        contained within institutional structures.

        The real-time verification approach means that when students leave courses
        or transfer between learning groups, their access permissions automatically
        adjust to reflect their current educational enrollment status.

        Args:
            bot: Telegram bot instance for API calls
            user_id: Telegram user ID to verify
            channel_id: Telegram channel ID to check membership against

        Returns:
            Boolean indicating whether user is an active channel member
        """
        try:
            member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)

            # Accept various levels of channel participation
            return member.status in [
                ChatMemberStatus.OWNER,  # Channel owner
                ChatMemberStatus.ADMINISTRATOR,  # Channel administrator
                ChatMemberStatus.MEMBER  # Channel subscriber/member
            ]
        except Exception as e:
            print(f"Error verifying channel membership: {e}")
            # Secure failure mode - deny access if verification fails
            return False

    @staticmethod
    def get_teacher_groups(teacher_phone):
        """
        Retrieve all learning groups managed by a specific teacher.

        This method supports the teacher workflow by providing access to all
        learning groups under their management. The chronological ordering
        ensures that recently created groups appear first, which typically
        corresponds to current semester or term activities.

        The error handling ensures that temporary database issues don't prevent
        teachers from accessing their group information, maintaining educational
        continuity even during system maintenance periods.
        """
        try:
            teacher = AuthSystem._get_teacher_by_phone(teacher_phone)
            if not teacher:
                return []

            groups = db.execute_query(
                "SELECT * FROM groups WHERE teacher_id = ? ORDER BY created_at DESC",
                (teacher['id'],)
            )
            return groups
        except Exception as e:
            print(f"Error retrieving teacher groups: {e}")
            return []

    @staticmethod
    def get_student_group(student_phone):
        """
        Retrieve the learning group associated with a specific student.

        Students typically belong to a single primary learning group, which
        defines their educational context and determines which channels, tasks,
        and educational resources they can access. This method provides the
        group information needed for student workflow management.
        """
        try:
            student = AuthSystem._get_student_by_phone(student_phone)
            if not student:
                return None

            return AuthSystem._get_group_by_id(student['group_id'])
        except Exception as e:
            print(f"Error retrieving student group: {e}")
            return None

    @staticmethod
    def set_user_session(user_id, group_id, session_type='normal'):
        """
        Establish session context for educational workflow management.

        Educational workflows often involve multiple steps that span several
        interactions. For example, when a teacher begins grading student
        submissions, they select a learning group and then work through
        multiple submissions within that context. Session management ensures
        that this context persists across interactions without requiring
        repetitive group selection.

        The session type parameter allows the system to adapt its interface
        and behavior based on the specific educational activity being performed.
        For instance, grading sessions might display different interface
        elements than general group management sessions.

        Args:
            user_id: Telegram user ID for session association
            group_id: Learning group ID for context
            session_type: Activity type ('normal' or 'grading')
        """
        try:
            # Clear any existing session to prevent context conflicts
            db.execute_query("DELETE FROM user_sessions WHERE user_id = ?", (user_id,))

            # Establish new session with current timestamp
            db.execute_query(
                "INSERT INTO user_sessions (user_id, selected_group_id, session_type) VALUES (?, ?, ?)",
                (user_id, group_id, session_type)
            )
        except Exception as e:
            print(f"Error establishing user session: {e}")

    @staticmethod
    def get_user_session(user_id):
        """
        Retrieve current session context for workflow continuity.

        This method enables the system to understand what educational context
        a user is currently working within. The session information guides
        interface decisions, determines which data to display, and ensures
        that user actions are applied to the correct learning group.

        Session retrieval is fundamental to creating seamless educational
        workflows where users don't need to repeatedly specify their working
        context for each operation.

        Args:
            user_id: Telegram user ID for session lookup

        Returns:
            Dictionary containing session details or None if no active session
        """
        try:
            sessions = db.execute_query(
                "SELECT * FROM user_sessions WHERE user_id = ?",
                (user_id,)
            )
            return sessions[0] if sessions else None
        except Exception as e:
            print(f"Error retrieving user session: {e}")
            return None

    @staticmethod
    def clear_user_session(user_id):
        """
        Clear session context for clean workflow transitions.

        Session clearing is essential for preventing context confusion when
        users transition between different educational activities or return
        to main navigation areas. By clearing session data at appropriate
        transition points, the system ensures that previous context doesn't
        inadvertently affect new activities.

        This is particularly important in educational settings where teachers
        work with multiple learning groups and need clear boundaries between
        different classroom contexts to prevent accidental cross-contamination
        of educational activities.

        Args:
            user_id: Telegram user ID for session clearing
        """
        try:
            db.execute_query("DELETE FROM user_sessions WHERE user_id = ?", (user_id,))
        except Exception as e:
            print(f"Error clearing user session: {e}")


# Create the global authentication instance for system-wide access
# This instance serves as the primary interface for all authentication
# and session management operations throughout the educational platform
auth = AuthSystem()