"""
Product defaults loader for iac_products_default_value repository
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional
from ..git_integration import FileLoader


class ProductDefaultsLoader:
    """Loads product default values from iac_products_default_value repository"""
    
    def __init__(self, file_loader: Optional[FileLoader] = None):
        self.file_loader = file_loader or FileLoader()
        self.logger = logging.getLogger(__name__)
    
    def load_defaults(self, repo_path: Path, project_name: str, 
                     resource_type: str, environment: str) -> Dict[str, Any]:
        """
        Load product default values for a specific resource type and environment
        
        Args:
            repo_path: Path to iac_products_default_value repository
            project_name: Project name (e.g., Enterprise_IT___IOPS___Orchestration)
            resource_type: Resource type (e.g., s3, ec2, rds)
            environment: Environment (e.g., dev, qa, prod)
            
        Returns:
            Dictionary of default values or empty dict if not found
        """
        self.logger.info(f"🔍 Loading product defaults for {project_name}/{resource_type}/{environment}")
        
        try:
            defaults = self.file_loader.load_product_defaults(
                repo_path, project_name, resource_type, environment
            )
            
            if defaults is None:
                self.logger.warning(f"No product defaults found for {resource_type}/{environment}")
                return {}
            
            self.logger.info(f"✅ Loaded product defaults: {len(defaults)} keys")
            self._log_default_summary(defaults, f"{resource_type}/{environment}")
            
            return defaults
            
        except Exception as e:
            self.logger.error(f"Failed to load product defaults: {e}")
            return {}
    
    def load_defaults_for_multiple_resources(self, repo_path: Path, project_name: str,
                                           resource_entries: list) -> Dict[str, Dict[str, Any]]:
        """
        Load defaults for multiple resource entries
        
        Args:
            repo_path: Path to iac_products_default_value repository
            project_name: Project name
            resource_entries: List of resource entry dictionaries
            
        Returns:
            Dictionary mapping resource keys to their defaults
        """
        results = {}
        
        for entry in resource_entries:
            resource_type = entry.get('type')
            environment = entry.get('env')
            resource_name = entry.get('resource_name')
            
            if not all([resource_type, environment, resource_name]):
                self.logger.warning(f"Skipping incomplete resource entry: {entry}")
                continue
            
            resource_key = f"{resource_type}_{resource_name}"
            
            defaults = self.load_defaults(repo_path, project_name, resource_type, environment)
            results[resource_key] = defaults
        
        self.logger.info(f"📦 Loaded defaults for {len(results)} resources")
        return results
    
    def get_available_environments(self, repo_path: Path, project_name: str, 
                                 resource_type: str) -> list:
        """
        Get list of available environments for a resource type
        
        Args:
            repo_path: Path to repository
            project_name: Project name
            resource_type: Resource type
            
        Returns:
            List of available environments
        """
        try:
            resource_path = repo_path / project_name / resource_type
            
            if not resource_path.exists():
                self.logger.warning(f"Resource type directory not found: {resource_path}")
                return []
            
            environments = []
            for env_dir in resource_path.iterdir():
                if env_dir.is_dir():
                    default_file = env_dir / "default.json"
                    if default_file.exists():
                        environments.append(env_dir.name)
            
            self.logger.debug(f"Available environments for {resource_type}: {environments}")
            return sorted(environments)
            
        except Exception as e:
            self.logger.error(f"Failed to get available environments: {e}")
            return []
    
    def get_available_resource_types(self, repo_path: Path, project_name: str) -> list:
        """
        Get list of available resource types for a project
        
        Args:
            repo_path: Path to repository
            project_name: Project name
            
        Returns:
            List of available resource types
        """
        try:
            project_path = repo_path / project_name
            
            if not project_path.exists():
                self.logger.warning(f"Project directory not found: {project_path}")
                return []
            
            resource_types = []
            for type_dir in project_path.iterdir():
                if type_dir.is_dir():
                    # Check if it has any environment subdirectories with default.json
                    has_defaults = any(
                        (type_dir / env_dir.name / "default.json").exists()
                        for env_dir in type_dir.iterdir()
                        if env_dir.is_dir()
                    )
                    if has_defaults:
                        resource_types.append(type_dir.name)
            
            self.logger.debug(f"Available resource types for {project_name}: {resource_types}")
            return sorted(resource_types)
            
        except Exception as e:
            self.logger.error(f"Failed to get available resource types: {e}")
            return []
    
    def validate_defaults_structure(self, repo_path: Path, project_name: str) -> Dict[str, Any]:
        """
        Validate the structure of product defaults repository
        
        Args:
            repo_path: Path to repository
            project_name: Project name
            
        Returns:
            Validation results
        """
        validation_result = {
            'is_valid': True,
            'project_exists': False,
            'resource_types': {},
            'errors': [],
            'warnings': []
        }
        
        try:
            project_path = repo_path / project_name
            validation_result['project_exists'] = project_path.exists()
            
            if not project_path.exists():
                validation_result['is_valid'] = False
                validation_result['errors'].append(f"Project directory not found: {project_name}")
                return validation_result
            
            # Validate resource types
            for type_dir in project_path.iterdir():
                if type_dir.is_dir():
                    resource_type = type_dir.name
                    validation_result['resource_types'][resource_type] = {
                        'environments': [],
                        'has_defaults': False,
                        'invalid_files': []
                    }
                    
                    # Check environments
                    for env_dir in type_dir.iterdir():
                        if env_dir.is_dir():
                            env_name = env_dir.name
                            default_file = env_dir / "default.json"
                            
                            if default_file.exists():
                                validation_result['resource_types'][resource_type]['environments'].append(env_name)
                                validation_result['resource_types'][resource_type]['has_defaults'] = True
                                
                                # Try to load the file
                                try:
                                    self.file_loader.load_json_file(repo_path, 
                                        f"{project_name}/{resource_type}/{env_name}/default.json")
                                except Exception as e:
                                    validation_result['resource_types'][resource_type]['invalid_files'].append({
                                        'file': f"{env_name}/default.json",
                                        'error': str(e)
                                    })
            
            # Check for warnings
            empty_types = [
                rt for rt, data in validation_result['resource_types'].items()
                if not data['has_defaults']
            ]
            if empty_types:
                validation_result['warnings'].append(f"Resource types without defaults: {empty_types}")
            
        except Exception as e:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"Validation failed: {e}")
        
        return validation_result
    
    def _log_default_summary(self, defaults: Dict[str, Any], context: str) -> None:
        """Log a summary of loaded defaults"""
        if not defaults:
            return
        
        summary_items = []
        for key, value in defaults.items():
            if isinstance(value, list):
                summary_items.append(f"{key}[{len(value)}]")
            elif isinstance(value, dict):
                summary_items.append(f"{key}{{{len(value)}}}")
            else:
                summary_items.append(f"{key}={value}")
        
        if len(summary_items) <= 5:
            summary = ", ".join(summary_items)
        else:
            summary = ", ".join(summary_items[:5]) + f", +{len(summary_items)-5} more"
        
        self.logger.debug(f"📋 {context} defaults: {summary}")