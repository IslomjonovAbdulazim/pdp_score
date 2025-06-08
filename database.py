import sqlite3
import os
from datetime import datetime, timezone


class Database:
    def __init__(self, db_path="education_bot.db"):
        """Initialize database connection and create tables if they don't exist"""
        self.db_path = db_path
        self.init_database()

    def get_connection(self):
        """Get database connection with foreign key support enabled"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints
        conn.row_factory = sqlite3.Row  # This allows us to access columns by name
        return conn

    def init_database(self):
        """Create all necessary tables with proper relationships"""
        conn = self.get_connection()

        try:
            # Admin table - simple static phone number storage
            conn.execute('''
                CREATE TABLE IF NOT EXISTS admins (
                    id INTEGER PRIMARY KEY,
                    phone_number TEXT UNIQUE NOT NULL
                )
            ''')

            # Teachers table - stores teacher info created by admin
            conn.execute('''
                CREATE TABLE IF NOT EXISTS teachers (
                    id INTEGER PRIMARY KEY,
                    phone_number TEXT UNIQUE NOT NULL,
                    fullname TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Groups table - each group belongs to a teacher and has a telegram channel
            conn.execute('''
                CREATE TABLE IF NOT EXISTS groups (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    channel_id TEXT NOT NULL,
                    teacher_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (teacher_id) REFERENCES teachers (id) ON DELETE CASCADE
                )
            ''')

            # Modules table - each group has multiple modules, auto incrementing
            conn.execute('''
                CREATE TABLE IF NOT EXISTS modules (
                    id INTEGER PRIMARY KEY,
                    group_id INTEGER NOT NULL,
                    module_number INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (group_id) REFERENCES groups (id) ON DELETE CASCADE,
                    UNIQUE(group_id, module_number)  -- Each module number unique per group
                )
            ''')

            # Tasks table - each module can have multiple tasks, but only one active per group
            conn.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY,
                    module_id INTEGER NOT NULL,
                    description TEXT NOT NULL,
                    photos TEXT,  -- JSON string of photo file_ids
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (module_id) REFERENCES modules (id) ON DELETE CASCADE
                )
            ''')

            # Students table - belongs to a group, must be in telegram channel
            conn.execute('''
                CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY,
                    phone_number TEXT NOT NULL,
                    fullname TEXT NOT NULL,
                    group_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (group_id) REFERENCES groups (id) ON DELETE CASCADE,
                    UNIQUE(phone_number, group_id)  -- Student can be in multiple groups
                )
            ''')

            # Submissions table - student submissions for tasks
            conn.execute('''
                CREATE TABLE IF NOT EXISTS submissions (
                    id INTEGER PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    student_id INTEGER NOT NULL,
                    photos TEXT,  -- JSON string of photo file_ids
                    description TEXT,
                    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_graded BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
                    FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE,
                    UNIQUE(task_id, student_id)  -- One submission per task per student
                )
            ''')

            # Grades table - teacher grades for submissions, stored per module
            conn.execute('''
                CREATE TABLE IF NOT EXISTS grades (
                    id INTEGER PRIMARY KEY,
                    submission_id INTEGER NOT NULL,
                    module_id INTEGER NOT NULL,
                    student_id INTEGER NOT NULL,
                    score INTEGER NOT NULL,
                    graded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (submission_id) REFERENCES submissions (id) ON DELETE CASCADE,
                    FOREIGN KEY (module_id) REFERENCES modules (id) ON DELETE CASCADE,
                    FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE,
                    UNIQUE(submission_id)  -- One grade per submission
                )
            ''')

            # User sessions table - to track current selected group for teachers
            conn.execute('''
                CREATE TABLE IF NOT EXISTS user_sessions (
                    user_id INTEGER PRIMARY KEY,
                    selected_group_id INTEGER,
                    session_type TEXT,  -- 'grading', 'normal'
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (selected_group_id) REFERENCES groups (id) ON DELETE SET NULL
                )
            ''')

            conn.commit()
            print("Database initialized successfully!")

        except Exception as e:
            print(f"Error initializing database: {e}")
            conn.rollback()
        finally:
            conn.close()

    def execute_query(self, query, params=None):
        """Execute a query and return results"""
        conn = self.get_connection()
        try:
            if params:
                cursor = conn.execute(query, params)
            else:
                cursor = conn.execute(query)

            # If it's a SELECT query, fetch results
            if query.strip().upper().startswith('SELECT'):
                results = cursor.fetchall()
                return [dict(row) for row in results]
            else:
                # For INSERT, UPDATE, DELETE operations
                conn.commit()
                return cursor.lastrowid

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get_utc_now(self):
        """Get current UTC timestamp for consistent time handling"""
        return datetime.now(timezone.utc).isoformat()


# Initialize database instance
db = Database()