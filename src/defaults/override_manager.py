"""
Override manager for iac_value_override repository
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional
from ..git_integration import FileLoader


class OverrideManager:
    """Manages value overrides from iac_value_override repository"""
    
    def __init__(self, file_loader: Optional[FileLoader] = None):
        self.file_loader = file_loader or FileLoader()
        self.logger = logging.getLogger(__name__)
    
    def load_enforced_defaults(self, repo_path: Path, resource_type: str) -> Dict[str, Any]:
        """
        Load enforced default values for a resource type
        
        Args:
            repo_path: Path to iac_value_override repository
            resource_type: Resource type (e.g., s3, ec2)
            
        Returns:
            Dictionary of enforced default values or empty dict if not found
        """
        self.logger.info(f"🔒 Loading enforced defaults for {resource_type}")
        
        try:
            defaults = self.file_loader.load_enforced_defaults(repo_path, resource_type)
            
            if defaults is None:
                self.logger.debug(f"No enforced defaults found for {resource_type}")
                return {}
            
            self.logger.info(f"✅ Loaded enforced defaults: {len(defaults)} keys")
            self._log_override_summary(defaults, f"{resource_type}/enforced")
            
            return defaults
            
        except Exception as e:
            self.logger.error(f"Failed to load enforced defaults for {resource_type}: {e}")
            return {}
    
    def load_cloud_project_defaults(self, repo_path: Path, resource_type: str, 
                                  cloud_project: str) -> Dict[str, Any]:
        """
        Load cloud project default values
        
        Args:
            repo_path: Path to iac_value_override repository
            resource_type: Resource type (e.g., s3, ec2)
            cloud_project: Cloud project name (e.g., cdk-aws-ghs-neb-lab)
            
        Returns:
            Dictionary of cloud project default values or empty dict if not found
        """
        self.logger.info(f"☁️ Loading cloud project defaults for {resource_type}/{cloud_project}")
        
        try:
            defaults = self.file_loader.load_cloud_project_defaults(
                repo_path, resource_type, cloud_project
            )
            
            if defaults is None:
                self.logger.debug(f"No cloud project defaults found for {resource_type}/{cloud_project}")
                return {}
            
            self.logger.info(f"✅ Loaded cloud project defaults: {len(defaults)} keys")
            self._log_override_summary(defaults, f"{resource_type}/{cloud_project}")
            
            return defaults
            
        except Exception as e:
            self.logger.error(f"Failed to load cloud project defaults for {resource_type}/{cloud_project}: {e}")
            return {}
    
    def load_resource_overrides(self, repo_path: Path, resource_type: str, 
                              cloud_project: str, resource_name: str) -> Dict[str, Any]:
        """
        Load specific resource override values
        
        Args:
            repo_path: Path to iac_value_override repository
            resource_type: Resource type (e.g., s3, ec2)
            cloud_project: Cloud project name (e.g., cdk-aws-ghs-neb-lab)
            resource_name: Resource name (e.g., aditya-test-dec3rd-s1)
            
        Returns:
            Dictionary of resource override values or empty dict if not found
        """
        self.logger.info(f"🎯 Loading resource overrides for {resource_type}/{cloud_project}/{resource_name}")
        
        try:
            overrides = self.file_loader.load_resource_overrides(
                repo_path, resource_type, cloud_project, resource_name
            )
            
            if overrides is None:
                self.logger.debug(f"No resource overrides found for {resource_name}")
                return {}
            
            self.logger.info(f"✅ Loaded resource overrides: {len(overrides)} keys")
            self._log_override_summary(overrides, f"{resource_type}/{cloud_project}/{resource_name}")
            
            return overrides
            
        except Exception as e:
            self.logger.error(f"Failed to load resource overrides for {resource_name}: {e}")
            return {}
    
    def load_all_overrides_for_resource(self, repo_path: Path, resource_type: str,
                                      cloud_project: str, resource_name: str) -> Dict[str, Dict[str, Any]]:
        """
        Load all override levels for a specific resource
        
        Args:
            repo_path: Path to iac_value_override repository
            resource_type: Resource type
            cloud_project: Cloud project name
            resource_name: Resource name
            
        Returns:
            Dictionary with all override levels
        """
        self.logger.info(f"📋 Loading all override levels for {resource_type}/{resource_name}")
        
        overrides = {
            'enforced_defaults': self.load_enforced_defaults(repo_path, resource_type),
            'cloud_project_defaults': self.load_cloud_project_defaults(repo_path, resource_type, cloud_project),
            'resource_overrides': self.load_resource_overrides(repo_path, resource_type, cloud_project, resource_name)
        }
        
        total_configs = sum(1 for config in overrides.values() if config)
        self.logger.info(f"📦 Loaded {total_configs}/3 override levels for {resource_name}")
        
        return overrides
    
    def get_available_cloud_projects(self, repo_path: Path, resource_type: str) -> list:
        """
        Get list of available cloud projects for a resource type
        
        Args:
            repo_path: Path to repository
            resource_type: Resource type
            
        Returns:
            List of available cloud projects
        """
        try:
            resource_path = repo_path / resource_type
            
            if not resource_path.exists():
                self.logger.warning(f"Resource type directory not found: {resource_path}")
                return []
            
            cloud_projects = []
            for project_dir in resource_path.iterdir():
                if project_dir.is_dir() and project_dir.name != "eit-enforced-default.json":
                    # Check if it has default.json or any resource files
                    has_files = any(
                        file.suffix == '.json' for file in project_dir.iterdir()
                        if file.is_file()
                    )
                    if has_files:
                        cloud_projects.append(project_dir.name)
            
            self.logger.debug(f"Available cloud projects for {resource_type}: {cloud_projects}")
            return sorted(cloud_projects)
            
        except Exception as e:
            self.logger.error(f"Failed to get available cloud projects: {e}")
            return []
    
    def get_available_resource_names(self, repo_path: Path, resource_type: str, 
                                   cloud_project: str) -> list:
        """
        Get list of available resource names for a resource type and cloud project
        
        Args:
            repo_path: Path to repository
            resource_type: Resource type
            cloud_project: Cloud project name
            
        Returns:
            List of available resource names
        """
        try:
            project_path = repo_path / resource_type / cloud_project
            
            if not project_path.exists():
                self.logger.warning(f"Cloud project directory not found: {project_path}")
                return []
            
            resource_names = []
            for file_path in project_path.iterdir():
                if file_path.is_file() and file_path.suffix == '.json' and file_path.name != 'default.json':
                    # Remove .json extension to get resource name
                    resource_names.append(file_path.stem)
            
            self.logger.debug(f"Available resources for {resource_type}/{cloud_project}: {resource_names}")
            return sorted(resource_names)
            
        except Exception as e:
            self.logger.error(f"Failed to get available resource names: {e}")
            return []
    
    def validate_override_structure(self, repo_path: Path) -> Dict[str, Any]:
        """
        Validate the structure of override repository
        
        Args:
            repo_path: Path to repository
            
        Returns:
            Validation results
        """
        validation_result = {
            'is_valid': True,
            'resource_types': {},
            'errors': [],
            'warnings': []
        }
        
        try:
            # Check resource types
            for type_dir in repo_path.iterdir():
                if type_dir.is_dir():
                    resource_type = type_dir.name
                    validation_result['resource_types'][resource_type] = {
                        'has_enforced_defaults': False,
                        'cloud_projects': {},
                        'invalid_files': []
                    }
                    
                    # Check for enforced defaults
                    enforced_file = type_dir / "eit-enforced-default.json"
                    if enforced_file.exists():
                        validation_result['resource_types'][resource_type]['has_enforced_defaults'] = True
                        try:
                            self.file_loader.load_json_file(repo_path, f"{resource_type}/eit-enforced-default.json")
                        except Exception as e:
                            validation_result['resource_types'][resource_type]['invalid_files'].append({
                                'file': 'eit-enforced-default.json',
                                'error': str(e)
                            })
                    
                    # Check cloud projects
                    for project_dir in type_dir.iterdir():
                        if project_dir.is_dir():
                            project_name = project_dir.name
                            validation_result['resource_types'][resource_type]['cloud_projects'][project_name] = {
                                'has_defaults': False,
                                'resource_files': [],
                                'invalid_files': []
                            }
                            
                            # Check files in cloud project
                            for file_path in project_dir.iterdir():
                                if file_path.is_file() and file_path.suffix == '.json':
                                    if file_path.name == 'default.json':
                                        validation_result['resource_types'][resource_type]['cloud_projects'][project_name]['has_defaults'] = True
                                    else:
                                        validation_result['resource_types'][resource_type]['cloud_projects'][project_name]['resource_files'].append(file_path.stem)
                                    
                                    # Validate JSON
                                    try:
                                        relative_path = file_path.relative_to(repo_path)
                                        self.file_loader.load_json_file(repo_path, str(relative_path))
                                    except Exception as e:
                                        validation_result['resource_types'][resource_type]['cloud_projects'][project_name]['invalid_files'].append({
                                            'file': file_path.name,
                                            'error': str(e)
                                        })
        
        except Exception as e:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"Validation failed: {e}")
        
        return validation_result
    
    def _log_override_summary(self, overrides: Dict[str, Any], context: str) -> None:
        """Log a summary of loaded overrides"""
        if not overrides:
            return
        
        summary_items = []
        for key, value in overrides.items():
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
        
        self.logger.debug(f"🔧 {context} overrides: {summary}")