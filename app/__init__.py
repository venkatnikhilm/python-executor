# app/__init__.py
"""
Python Executor Service

A secure REST API for executing arbitrary Python scripts in a sandboxed environment.
Uses nsjail for isolation and resource limiting.
"""

__version__ = "1.0.0"

from app.main import app
from app.executor import ScriptExecutor

__all__ = ['app', 'ScriptExecutor']