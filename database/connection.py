# database/connection.py
import sqlite3
import os
from typing import Optional


class DatabaseConnection:
    _instance: Optional['DatabaseConnection'] = None
    _connection: Optional[sqlite3.Connection] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._connection is None:
            self.connect()

    def connect(self):
        """Create connection to SQLite database"""
        db_path = os.path.join('data', 'bot.db')

        # Create data directory if it doesn't exist
        os.makedirs('data', exist_ok=True)

        self._connection = sqlite3.connect(
            db_path,
            check_same_thread=False,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )

        # Enable foreign key constraints
        self._connection.execute("PRAGMA foreign_keys = ON")

        # Set row factory for dictionary-like access
        self._connection.row_factory = sqlite3.Row

        print(f"Database connected: {db_path}")

    def get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        if self._connection is None:
            self.connect()
        return self._connection

    def execute_query(self, query: str, params: tuple = ()):
        """Execute a single query"""
        cursor = self.get_connection().cursor()
        try:
            cursor.execute(query, params)
            self._connection.commit()
            return cursor
        except Exception as e:
            self._connection.rollback()
            print(f"Database error: {e}")
            raise

    def fetch_one(self, query: str, params: tuple = ()):
        """Fetch single row"""
        cursor = self.execute_query(query, params)
        return cursor.fetchone()

    def fetch_all(self, query: str, params: tuple = ()):
        """Fetch all rows"""
        cursor = self.execute_query(query, params)
        return cursor.fetchall()

    def close(self):
        """Close database connection"""
        if self._connection:
            self._connection.close()
            self._connection = None
            print("Database connection closed")


# Global database instance
db = DatabaseConnection()