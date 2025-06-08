# bot/middlewares/__init__.py
from .auth import auth, AuthMiddleware

__all__ = ['auth', 'AuthMiddleware']