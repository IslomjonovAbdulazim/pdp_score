# database/__init__.py
from .connection import db
from .models import *
from .migrations import initialize_database

__all__ = ['db', 'initialize_database']