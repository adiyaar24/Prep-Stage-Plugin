"""
File loading utilities for JSON files from Git repositories
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List


class FileLoadError(Exception):
    """Custom exception for file loading errors"""
    pass


class FileLoader:
    """Loads and parses JSON files from Git repositories"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def load_json_file(self, repo_path: Path, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Load and parse a JSON file from repository
        
        Args:
            repo_path: Path to the repository root
            file_path: Relative path to the JSON file within repository
            
        Returns:
            Parsed JSON data or None if file doesn't exist
            
        Raises:
            FileLoadError: If file exists but cannot be parsed
        """
        full_path = repo_path / file_path
        
        try:
            if not full_path.exists():
                self.logger.debug(f"File not found: {file_path}")
                return None
            
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            if not content:
                self.logger.warning(f"Empty file: {file_path}")
                return {}
            
            data = json.loads(content)
            self.logger.debug(f"✅ Loaded JSON file: {file_path}")
            return data
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parsing error in {file_path}: {e}")
            raise FileLoadError(f"Invalid JSON in {file_path}: {e}")
        except Exception as e:
            self.logger.error(f"Failed to load file {file_path}: {e}")
            raise FileLoadError(f"Failed to load {file_path}: {e}")
    
    def load_product_defaults(self, repo_path: Path, project_name: str, 
                            resource_type: str, environment: str) -> Optional[Dict[str, Any]]:
        """
        Load product default values
        
        Args:
            repo_path: Path to iac_products_default_value repository
            project_name: Project name (e.g., Enterprise_IT___IOPS___Orchestration)
            resource_type: Resource type (e.g., s3)
            environment: Environment (e.g., dev, prod)
            
        Returns:
            Product default values or None if not found
        """
        file_path = f"{project_name}/{resource_type}/{environment}/default.json"
        
        self.logger.info(f"🔍 Loading product defaults: {file_path}")
        return self.load_json_file(repo_path, file_path)
    
    def load_enforced_defaults(self, repo_path: Path, resource_type: str) -> Optional[Dict[str, Any]]:
        """
        Load enforced default values
        
        Args:
            repo_path: Path to iac_value_override repository
            resource_type: Resource type (e.g., s3)
            
        Returns:
            Enforced default values or None if not found
        """
        file_path = f"{resource_type}/eit-enforced-default.json"
        
        self.logger.info(f"🔍 Loading enforced defaults: {file_path}")
        return self.load_json_file(repo_path, file_path)
    
    def load_cloud_project_defaults(self, repo_path: Path, resource_type: str, 
                                  cloud_project: str) -> Optional[Dict[str, Any]]:
        """
        Load cloud project default values
        
        Args:
            repo_path: Path to iac_value_override repository
            resource_type: Resource type (e.g., s3)
            cloud_project: Cloud project name (e.g., cdk-aws-ghs-neb-lab)
            
        Returns:
            Cloud project default values or None if not found
        """
        file_path = f"{resource_type}/{cloud_project}/default.json"
        
        self.logger.info(f"🔍 Loading cloud project defaults: {file_path}")
        return self.load_json_file(repo_path, file_path)
    
    def load_resource_overrides(self, repo_path: Path, resource_type: str, 
                              cloud_project: str, resource_name: str) -> Optional[Dict[str, Any]]:
        """
        Load specific resource override values
        
        Args:
            repo_path: Path to iac_value_override repository
            resource_type: Resource type (e.g., s3)
            cloud_project: Cloud project name (e.g., cdk-aws-ghs-neb-lab)
            resource_name: Resource name (e.g., aditya-test-dec3rd-s1)
            
        Returns:
            Resource override values or None if not found
        """
        file_path = f"{resource_type}/{cloud_project}/{resource_name}.json"
        
        self.logger.info(f"🔍 Loading resource overrides: {file_path}")
        return self.load_json_file(repo_path, file_path)
    
    def list_available_files(self, repo_path: Path, pattern: str = "**/*.json") -> List[str]:
        """
        List all available JSON files in repository
        
        Args:
            repo_path: Path to repository
            pattern: Glob pattern for files
            
        Returns:
            List of relative file paths
        """
        try:
            files = []
            for file_path in repo_path.glob(pattern):
                if file_path.is_file():
                    relative_path = file_path.relative_to(repo_path)
                    files.append(str(relative_path))
            
            self.logger.debug(f"Found {len(files)} JSON files in {repo_path.name}")
            return sorted(files)
            
        except Exception as e:
            self.logger.error(f"Failed to list files in {repo_path}: {e}")
            return []
    
    def validate_file_structure(self, repo_path: Path) -> Dict[str, Any]:
        """
        Validate repository file structure
        
        Args:
            repo_path: Path to repository
            
        Returns:
            Validation results
        """
        results = {
            'repository_path': str(repo_path),
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'file_count': 0,
            'invalid_json_files': []
        }
        
        try:
            json_files = self.list_available_files(repo_path)
            results['file_count'] = len(json_files)
            
            for file_path in json_files:
                try:
                    self.load_json_file(repo_path, file_path)
                except FileLoadError as e:
                    results['invalid_json_files'].append({
                        'file': file_path,
                        'error': str(e)
                    })
                    results['is_valid'] = False
            
            if results['invalid_json_files']:
                results['errors'].append(f"Found {len(results['invalid_json_files'])} invalid JSON files")
            
        except Exception as e:
            results['is_valid'] = False
            results['errors'].append(f"Failed to validate repository: {e}")
        
        return results