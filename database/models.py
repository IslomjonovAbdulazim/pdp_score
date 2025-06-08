# database/models.py
import sqlite3
from datetime import datetime
from typing import Optional, List
from enum import Enum
import json

class UserRole(Enum):
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"

class ModuleStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

# Base User Model
class User:
    def __init__(self, user_id: int, telegram_id: int, full_name: str,
                 phone_number: str, role: UserRole, telegram_group_id: int,
                 created_at: datetime = None):
        self.user_id = user_id
        self.telegram_id = telegram_id
        self.full_name = full_name
        self.phone_number = phone_number
        self.role = role.value
        self.telegram_group_id = telegram_group_id
        self.created_at = created_at or datetime.now()
        self.is_active = True

# Group Model (Class Groups)
class Group:
    def __init__(self, group_id: int, group_name: str, teacher_id: int,
                 telegram_group_id: int, created_at: datetime = None):
        self.group_id = group_id
        self.group_name = group_name
        self.teacher_id = teacher_id  # Foreign key to User
        self.telegram_group_id = telegram_group_id
        self.created_at = created_at or datetime.now()
        self.is_active = True

# Module Model (Sequential per group)
class Module:
    def __init__(self, module_id: int, group_id: int, module_number: int,
                 status: ModuleStatus, created_at: datetime = None,
                 ended_at: datetime = None):
        self.module_id = module_id
        self.group_id = group_id  # Foreign key to Group
        self.module_number = module_number  # Auto-increment per group
        self.module_name = f"Module {module_number}"
        self.status = status.value
        self.created_at = created_at or datetime.now()
        self.ended_at = ended_at

# Assignment Model (One active per group)
class Assignment:
    def __init__(self, assignment_id: int, group_id: int, module_id: int,
                 title: str, description: str, deadline: datetime,
                 max_points: int = 20, created_at: datetime = None):
        self.assignment_id = assignment_id
        self.group_id = group_id  # Foreign key to Group
        self.module_id = module_id  # Foreign key to Module
        self.title = title
        self.description = description
        self.deadline = deadline
        self.max_points = max_points
        self.telegram_file_ids = ""  # JSON string of file IDs
        self.created_at = created_at or datetime.now()
        self.is_active = True

# Submission Model (Queue system)
class Submission:
    def __init__(self, submission_id: int, assignment_id: int, student_id: int,
                 explanation: str, submitted_at: datetime = None):
        self.submission_id = submission_id
        self.assignment_id = assignment_id  # Foreign key to Assignment
        self.student_id = student_id  # Foreign key to User
        self.explanation = explanation
        self.telegram_file_ids = ""  # JSON string of file IDs
        self.submitted_at = submitted_at or datetime.now()
        self.is_graded = False
        self.queue_position = 0  # Auto-calculated

# Grade Model
class Grade:
    def __init__(self, grade_id: int, submission_id: int, teacher_id: int,
                 points_earned: float, teacher_feedback: str = "",
                 graded_at: datetime = None):
        self.grade_id = grade_id
        self.submission_id = submission_id  # Foreign key to Submission
        self.teacher_id = teacher_id  # Foreign key to User
        self.points_earned = points_earned
        self.max_points = 20  # Default, can be updated from assignment
        self.teacher_feedback = teacher_feedback
        self.late_penalty_applied = 0.0  # Percentage (0.3 for 30% penalty)
        self.final_score = points_earned  # After penalty calculation
        self.graded_at = graded_at or datetime.now()

# Student Group Membership (Many-to-Many relationship)
class StudentGroupMembership:
    def __init__(self, membership_id: int, student_id: int, group_id: int,
                 joined_at: datetime = None):
        self.membership_id = membership_id
        self.student_id = student_id  # Foreign key to User
        self.group_id = group_id  # Foreign key to Group
        self.joined_at = joined_at or datetime.now()
        self.is_active = True