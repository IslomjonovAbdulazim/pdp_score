# database/migrations.py
from database.connection import db


def create_tables():
    """Create all database tables"""

    # Users table (admins, teachers, students)
    users_table = """
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE NOT NULL,
        full_name TEXT NOT NULL,
        phone_number TEXT NOT NULL,
        role TEXT NOT NULL CHECK (role IN ('admin', 'teacher', 'student')),
        telegram_group_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_active BOOLEAN DEFAULT 1
    );
    """

    # Groups table (class groups)
    groups_table = """
    CREATE TABLE IF NOT EXISTS groups (
        group_id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_name TEXT NOT NULL,
        teacher_id INTEGER NOT NULL,
        telegram_group_id INTEGER UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_active BOOLEAN DEFAULT 1,
        FOREIGN KEY (teacher_id) REFERENCES users (user_id)
    );
    """

    # Modules table (sequential per group)
    modules_table = """
    CREATE TABLE IF NOT EXISTS modules (
        module_id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id INTEGER NOT NULL,
        module_number INTEGER NOT NULL,
        module_name TEXT NOT NULL,
        status TEXT NOT NULL CHECK (status IN ('active', 'inactive')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        ended_at TIMESTAMP NULL,
        FOREIGN KEY (group_id) REFERENCES groups (group_id),
        UNIQUE(group_id, module_number)
    );
    """

    # Assignments table (one active per group)
    assignments_table = """
    CREATE TABLE IF NOT EXISTS assignments (
        assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id INTEGER NOT NULL,
        module_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        deadline TIMESTAMP NOT NULL,
        max_points INTEGER DEFAULT 20,
        telegram_file_ids TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_active BOOLEAN DEFAULT 1,
        FOREIGN KEY (group_id) REFERENCES groups (group_id),
        FOREIGN KEY (module_id) REFERENCES modules (module_id)
    );
    """

    # Submissions table (queue system)
    submissions_table = """
    CREATE TABLE IF NOT EXISTS submissions (
        submission_id INTEGER PRIMARY KEY AUTOINCREMENT,
        assignment_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        explanation TEXT NOT NULL,
        telegram_file_ids TEXT DEFAULT '',
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_graded BOOLEAN DEFAULT 0,
        queue_position INTEGER DEFAULT 0,
        FOREIGN KEY (assignment_id) REFERENCES assignments (assignment_id),
        FOREIGN KEY (student_id) REFERENCES users (user_id),
        UNIQUE(assignment_id, student_id)
    );
    """

    # Grades table
    grades_table = """
    CREATE TABLE IF NOT EXISTS grades (
        grade_id INTEGER PRIMARY KEY AUTOINCREMENT,
        submission_id INTEGER UNIQUE NOT NULL,
        teacher_id INTEGER NOT NULL,
        points_earned REAL NOT NULL,
        max_points INTEGER DEFAULT 20,
        teacher_feedback TEXT DEFAULT '',
        late_penalty_applied REAL DEFAULT 0.0,
        final_score REAL NOT NULL,
        graded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (submission_id) REFERENCES submissions (submission_id),
        FOREIGN KEY (teacher_id) REFERENCES users (user_id)
    );
    """

    # Student group membership (many-to-many)
    memberships_table = """
    CREATE TABLE IF NOT EXISTS student_group_memberships (
        membership_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        group_id INTEGER NOT NULL,
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_active BOOLEAN DEFAULT 1,
        FOREIGN KEY (student_id) REFERENCES users (user_id),
        FOREIGN KEY (group_id) REFERENCES groups (group_id),
        UNIQUE(student_id, group_id)
    );
    """

    # Execute all table creation queries
    tables = [
        users_table,
        groups_table,
        modules_table,
        assignments_table,
        submissions_table,
        grades_table,
        memberships_table
    ]

    try:
        for table_sql in tables:
            db.execute_query(table_sql)

        print("All tables created successfully!")

    except Exception as e:
        print(f"Error creating tables: {e}")
        raise


def create_indexes():
    """Create database indexes for better performance"""

    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users (telegram_id);",
        "CREATE INDEX IF NOT EXISTS idx_users_role ON users (role);",
        "CREATE INDEX IF NOT EXISTS idx_groups_teacher ON groups (teacher_id);",
        "CREATE INDEX IF NOT EXISTS idx_modules_group ON modules (group_id);",
        "CREATE INDEX IF NOT EXISTS idx_modules_status ON modules (status);",
        "CREATE INDEX IF NOT EXISTS idx_assignments_group ON assignments (group_id);",
        "CREATE INDEX IF NOT EXISTS idx_assignments_active ON assignments (is_active);",
        "CREATE INDEX IF NOT EXISTS idx_submissions_assignment ON submissions (assignment_id);",
        "CREATE INDEX IF NOT EXISTS idx_submissions_student ON submissions (student_id);",
        "CREATE INDEX IF NOT EXISTS idx_submissions_graded ON submissions (is_graded);",
        "CREATE INDEX IF NOT EXISTS idx_grades_submission ON grades (submission_id);",
        "CREATE INDEX IF NOT EXISTS idx_memberships_student ON student_group_memberships (student_id);",
        "CREATE INDEX IF NOT EXISTS idx_memberships_group ON student_group_memberships (group_id);"
    ]

    try:
        for index_sql in indexes:
            db.execute_query(index_sql)

        print("All indexes created successfully!")

    except Exception as e:
        print(f"Error creating indexes: {e}")


def initialize_database():
    """Initialize complete database with tables and indexes"""
    print("Initializing database...")
    create_tables()
    create_indexes()
    print("Database initialization complete!")


if __name__ == "__main__":
    initialize_database()