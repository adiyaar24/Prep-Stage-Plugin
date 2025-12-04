"""
Git Manager for cloning and updating repositories
"""

import os
import subprocess
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse


class GitError(Exception):
    """Custom exception for git operations"""
    pass


class GitManager:
    """Manages git repository operations for the plugin"""
    
    def __init__(self, username: str, token: str, work_dir: str = "."):
        self.username = username
        self.token = token
        self.work_dir = Path(work_dir)
        self.logger = logging.getLogger(__name__)
        
        # Ensure work directory exists (current directory by default)
        self.work_dir.mkdir(parents=True, exist_ok=True)
    
    def clone_repository(self, repo_url: str, repo_name: str) -> Path:
        """
        Clone repository (fresh clone each time for simplicity)
        
        Args:
            repo_url: Git repository URL
            repo_name: Local name for the repository
            
        Returns:
            Path to the local repository directory
            
        Raises:
            GitError: If git operations fail
        """
        repo_path = self.work_dir / repo_name
        
        try:
            # Remove existing directory if it exists
            if repo_path.exists():
                import shutil
                shutil.rmtree(repo_path)
                self.logger.info(f"🗑️ Removed existing repository: {repo_name}")
            
            self.logger.info(f"📥 Cloning repository: {repo_name}")
            self._git_clone(repo_url, repo_path)
            
            return repo_path
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Git operation failed for {repo_name}: {e}")
            raise GitError(f"Failed to clone repository {repo_name}: {e}")
    
    def _git_clone(self, repo_url: str, repo_path: Path) -> None:
        """Clone repository with authentication"""
        # Create authenticated URL
        auth_url = self._create_authenticated_url(repo_url)
        
        cmd = [
            'git', 'clone',
            '--depth', '1',  # Shallow clone for performance
            '--single-branch',
            auth_url,
            str(repo_path)
        ]
        
        self.logger.debug(f"Executing: git clone --depth 1 --single-branch [URL] {repo_path}")
        
        # Set environment variables for git
        env = os.environ.copy()
        env['GIT_TERMINAL_PROMPT'] = '0'  # Disable interactive prompts
        
        subprocess.run(cmd, check=True, capture_output=True, text=True, env=env)
        self.logger.info(f"✅ Successfully cloned repository to {repo_path}")
    
    def _create_authenticated_url(self, repo_url: str) -> str:
        """Create URL with embedded authentication"""
        parsed = urlparse(repo_url)
        
        # Create authenticated URL: https://username:token@host/path
        auth_url = f"{parsed.scheme}://{self.username}:{self.token}@{parsed.netloc}{parsed.path}"
        
        return auth_url
    
    def cleanup_repositories(self, repo_names: List[str]) -> None:
        """
        Clean up specific repository directories
        
        Args:
            repo_names: List of repository names to clean up
        """
        try:
            import shutil
            for repo_name in repo_names:
                repo_path = self.work_dir / repo_name
                if repo_path.exists() and repo_path.is_dir():
                    shutil.rmtree(repo_path)
                    self.logger.info(f"🧹 Cleaned up repository: {repo_name}")
        except Exception as e:
            self.logger.warning(f"Failed to cleanup repositories: {e}")
    
    def validate_repository_access(self, repo_url: str) -> bool:
        """
        Validate that we can access the repository
        
        Args:
            repo_url: Repository URL to validate
            
        Returns:
            True if repository is accessible, False otherwise
        """
        try:
            auth_url = self._create_authenticated_url(repo_url)
            
            cmd = ['git', 'ls-remote', '--heads', auth_url]
            
            env = os.environ.copy()
            env['GIT_TERMINAL_PROMPT'] = '0'
            
            subprocess.run(cmd, check=True, capture_output=True, text=True, env=env)
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Repository validation failed for {repo_url}: {e}")
            return False
    
    def get_repository_info(self, repo_path: Path) -> Dict[str, Any]:
        """
        Get information about a local repository
        
        Args:
            repo_path: Path to local repository
            
        Returns:
            Dictionary with repository information
        """
        try:
            # Get last commit info
            cmd = ['git', 'log', '-1', '--format=%H,%an,%ad', '--date=iso']
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                check=True,
                capture_output=True,
                text=True
            )
            
            commit_info = result.stdout.strip().split(',')
            
            return {
                'path': str(repo_path),
                'last_commit_hash': commit_info[0] if len(commit_info) > 0 else 'unknown',
                'last_author': commit_info[1] if len(commit_info) > 1 else 'unknown',
                'last_commit_date': commit_info[2] if len(commit_info) > 2 else 'unknown',
                'exists': repo_path.exists(),
                'size_mb': sum(f.stat().st_size for f in repo_path.rglob('*') if f.is_file()) / (1024 * 1024)
            }
            
        except Exception as e:
            self.logger.warning(f"Failed to get repository info for {repo_path}: {e}")
            return {
                'path': str(repo_path),
                'exists': repo_path.exists(),
                'error': str(e)
            }