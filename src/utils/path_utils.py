"""
Path utilities for file and directory operations
"""

import os
import shutil
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any


class PathUtils:
    """Utility functions for path and file operations"""
    
    @staticmethod
    def ensure_directory(path: Path, mode: int = 0o755) -> bool:
        """
        Ensure directory exists, create if needed
        
        Args:
            path: Directory path
            mode: Directory permissions
            
        Returns:
            True if directory exists/created successfully
        """
        logger = logging.getLogger(__name__)
        
        try:
            if path.exists():
                if path.is_dir():
                    return True
                else:
                    logger.error(f"Path exists but is not a directory: {path}")
                    return False
            
            path.mkdir(parents=True, exist_ok=True, mode=mode)
            logger.debug(f"Created directory: {path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create directory {path}: {e}")
            return False
    
    @staticmethod
    def safe_remove_directory(path: Path, max_depth: int = 10) -> bool:
        """
        Safely remove directory and contents
        
        Args:
            path: Directory path to remove
            max_depth: Maximum depth to prevent infinite recursion
            
        Returns:
            True if successfully removed
        """
        logger = logging.getLogger(__name__)
        
        try:
            if not path.exists():
                return True
            
            if not path.is_dir():
                logger.warning(f"Path is not a directory: {path}")
                return False
            
            # Safety check: prevent removing important system directories
            if PathUtils._is_protected_path(path):
                logger.error(f"Refusing to remove protected path: {path}")
                return False
            
            # Check depth
            if len(path.parts) < 3:  # e.g., / or /usr
                logger.error(f"Path too shallow for safe removal: {path}")
                return False
            
            shutil.rmtree(path)
            logger.debug(f"Removed directory: {path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove directory {path}: {e}")
            return False
    
    @staticmethod
    def _is_protected_path(path: Path) -> bool:
        """Check if path is protected from deletion"""
        protected_paths = {
            '/', '/bin', '/usr', '/etc', '/var', '/home', '/root',
            '/boot', '/dev', '/proc', '/sys', '/tmp'
        }
        
        return str(path.resolve()) in protected_paths
    
    @staticmethod
    def get_directory_size(path: Path) -> Dict[str, Any]:
        """
        Get directory size information
        
        Args:
            path: Directory path
            
        Returns:
            Dictionary with size information
        """
        logger = logging.getLogger(__name__)
        
        result = {
            'total_size_bytes': 0,
            'total_size_mb': 0.0,
            'file_count': 0,
            'dir_count': 0,
            'error': None
        }
        
        try:
            if not path.exists() or not path.is_dir():
                result['error'] = f"Directory does not exist: {path}"
                return result
            
            total_size = 0
            file_count = 0
            dir_count = 0
            
            for item in path.rglob('*'):
                if item.is_file():
                    total_size += item.stat().st_size
                    file_count += 1
                elif item.is_dir():
                    dir_count += 1
            
            result['total_size_bytes'] = total_size
            result['total_size_mb'] = round(total_size / (1024 * 1024), 2)
            result['file_count'] = file_count
            result['dir_count'] = dir_count
            
        except Exception as e:
            logger.error(f"Failed to get directory size for {path}: {e}")
            result['error'] = str(e)
        
        return result
    
    @staticmethod
    def find_files_by_pattern(base_path: Path, pattern: str, 
                             max_results: int = 1000) -> List[Path]:
        """
        Find files matching pattern
        
        Args:
            base_path: Base directory to search
            pattern: Glob pattern to match
            max_results: Maximum number of results
            
        Returns:
            List of matching file paths
        """
        logger = logging.getLogger(__name__)
        
        try:
            if not base_path.exists() or not base_path.is_dir():
                logger.warning(f"Base path does not exist or is not a directory: {base_path}")
                return []
            
            matches = []
            count = 0
            
            for file_path in base_path.glob(pattern):
                if file_path.is_file():
                    matches.append(file_path)
                    count += 1
                    if count >= max_results:
                        logger.warning(f"Reached maximum results limit ({max_results})")
                        break
            
            logger.debug(f"Found {len(matches)} files matching '{pattern}' in {base_path}")
            return matches
            
        except Exception as e:
            logger.error(f"Failed to find files with pattern '{pattern}': {e}")
            return []
    
    @staticmethod
    def get_relative_path(file_path: Path, base_path: Path) -> Optional[str]:
        """
        Get relative path from base path
        
        Args:
            file_path: File path
            base_path: Base path
            
        Returns:
            Relative path string or None if not relative
        """
        try:
            return str(file_path.relative_to(base_path))
        except ValueError:
            return None
    
    @staticmethod
    def sanitize_filename(filename: str, replacement: str = '_') -> str:
        """
        Sanitize filename for safe file system usage
        
        Args:
            filename: Original filename
            replacement: Replacement character for invalid chars
            
        Returns:
            Sanitized filename
        """
        if not filename:
            return "unnamed_file"
        
        # Invalid characters for most file systems
        invalid_chars = '<>:"/\\|?*'
        
        # Replace invalid characters
        sanitized = filename
        for char in invalid_chars:
            sanitized = sanitized.replace(char, replacement)
        
        # Handle reserved names on Windows
        reserved_names = {
            'CON', 'PRN', 'AUX', 'NUL',
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        }
        
        name_without_ext = sanitized.rsplit('.', 1)[0].upper()
        if name_without_ext in reserved_names:
            sanitized = f"{replacement}{sanitized}"
        
        # Limit length
        if len(sanitized) > 255:
            name, ext = os.path.splitext(sanitized)
            sanitized = name[:255-len(ext)] + ext
        
        return sanitized
    
    @staticmethod
    def is_safe_path(path: Path, base_path: Path) -> bool:
        """
        Check if path is safe (within base path, no traversal attacks)
        
        Args:
            path: Path to check
            base_path: Base path that should contain the path
            
        Returns:
            True if path is safe
        """
        try:
            # Resolve both paths to handle symlinks and relative paths
            resolved_path = path.resolve()
            resolved_base = base_path.resolve()
            
            # Check if path is within base path
            return str(resolved_path).startswith(str(resolved_base))
            
        except Exception:
            return False
    
    @staticmethod
    def backup_file(file_path: Path, backup_suffix: str = '.backup') -> Optional[Path]:
        """
        Create backup of file
        
        Args:
            file_path: File to backup
            backup_suffix: Suffix for backup file
            
        Returns:
            Path to backup file or None if failed
        """
        logger = logging.getLogger(__name__)
        
        try:
            if not file_path.exists() or not file_path.is_file():
                logger.warning(f"File does not exist for backup: {file_path}")
                return None
            
            backup_path = file_path.with_suffix(file_path.suffix + backup_suffix)
            
            # If backup already exists, add timestamp
            if backup_path.exists():
                import time
                timestamp = int(time.time())
                backup_path = file_path.with_suffix(f"{file_path.suffix}{backup_suffix}.{timestamp}")
            
            shutil.copy2(file_path, backup_path)
            logger.debug(f"Created backup: {backup_path}")
            
            return backup_path
            
        except Exception as e:
            logger.error(f"Failed to create backup of {file_path}: {e}")
            return None