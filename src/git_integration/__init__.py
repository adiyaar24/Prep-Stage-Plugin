"""
Git integration module for repository management and file operations
"""

from .git_manager import GitManager
from .file_loader import FileLoader

__all__ = ['GitManager', 'FileLoader']