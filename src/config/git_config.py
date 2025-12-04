"""
Git-specific configuration and validation
"""

import logging
from typing import Dict, Any, Optional
from urllib.parse import urlparse


class GitConfiguration:
    """Handles Git-specific configuration and validation"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def validate_git_config(self, username: str, token: str, repo_urls: list) -> Dict[str, Any]:
        """
        Validate Git configuration
        
        Args:
            username: Git username
            token: Git token
            repo_urls: List of repository URLs to validate
            
        Returns:
            Validation results dictionary
        """
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Validate username
        if not username or not isinstance(username, str):
            validation_result['is_valid'] = False
            validation_result['errors'].append("Git username is required and must be a non-empty string")
        
        # Validate token
        if not token or not isinstance(token, str):
            validation_result['is_valid'] = False
            validation_result['errors'].append("Git token is required and must be a non-empty string")
        elif len(token) < 10:  # Basic sanity check
            validation_result['warnings'].append("Git token seems unusually short")
        
        # Validate repository URLs
        for i, repo_url in enumerate(repo_urls):
            url_validation = self._validate_repository_url(repo_url)
            if not url_validation['is_valid']:
                validation_result['is_valid'] = False
                validation_result['errors'].extend([
                    f"Repository {i+1}: {error}" for error in url_validation['errors']
                ])
            validation_result['warnings'].extend([
                f"Repository {i+1}: {warning}" for warning in url_validation.get('warnings', [])
            ])
        
        return validation_result
    
    def _validate_repository_url(self, repo_url: str) -> Dict[str, Any]:
        """
        Validate a single repository URL
        
        Args:
            repo_url: Repository URL to validate
            
        Returns:
            Validation results
        """
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': []
        }
        
        try:
            if not repo_url or not isinstance(repo_url, str):
                validation_result['is_valid'] = False
                validation_result['errors'].append("Repository URL is required")
                return validation_result
            
            parsed = urlparse(repo_url)
            
            # Check scheme
            if parsed.scheme not in ['http', 'https']:
                validation_result['is_valid'] = False
                validation_result['errors'].append(f"Invalid URL scheme: {parsed.scheme}. Must be http or https")
            
            # Check host
            if not parsed.netloc:
                validation_result['is_valid'] = False
                validation_result['errors'].append("Invalid URL: missing hostname")
            elif 'git.harness.io' not in parsed.netloc:
                validation_result['warnings'].append(f"Unexpected hostname: {parsed.netloc}")
            
            # Check path
            if not parsed.path or not parsed.path.endswith('.git'):
                validation_result['is_valid'] = False
                validation_result['errors'].append("Invalid Git repository URL: must end with .git")
            
            # Check for expected path structure
            if 'iac_products_default_value.git' in repo_url:
                if 'CDK_Prod' not in repo_url:
                    validation_result['warnings'].append("Products repo URL doesn't contain expected 'CDK_Prod' path")
            elif 'iac_value_override.git' in repo_url:
                if 'CDK_Prod' not in repo_url:
                    validation_result['warnings'].append("Overrides repo URL doesn't contain expected 'CDK_Prod' path")
            else:
                validation_result['warnings'].append("Repository URL doesn't match expected patterns")
        
        except Exception as e:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"URL validation failed: {e}")
        
        return validation_result
    
    def extract_cloud_project_from_config(self, resource_config: Dict[str, Any]) -> Optional[str]:
        """
        Extract cloud project from resource configuration
        
        Args:
            resource_config: Resource configuration dictionary
            
        Returns:
            Cloud project name or None if not found
        """
        try:
            entries = resource_config.get('entries', [])
            if not entries:
                return None
            
            # Look for cloud_project in first entry
            first_entry = entries[0]
            cloud_project = first_entry.get('cloud_project')
            
            if cloud_project:
                self.logger.debug(f"Extracted cloud project from config: {cloud_project}")
                return cloud_project
            
            # Try to extract from other common fields
            for field_name in ['aws_account', 'cloud_account', 'account_name']:
                if field_name in first_entry:
                    cloud_project = first_entry[field_name]
                    self.logger.debug(f"Extracted cloud project from {field_name}: {cloud_project}")
                    return cloud_project
            
            self.logger.warning("No cloud project found in resource configuration")
            return None
        
        except Exception as e:
            self.logger.error(f"Failed to extract cloud project from config: {e}")
            return None
    
    def extract_project_name_from_workflow(self, workflow_data: Optional[Dict[str, Any]] = None) -> str:
        """
        Extract project name from workflow metadata
        
        Args:
            workflow_data: Workflow metadata (optional)
            
        Returns:
            Project name
        """
        # Default project name
        default_project = "Enterprise_IT___IOPS___Orchestration"
        
        if not workflow_data:
            self.logger.debug(f"No workflow data provided, using default project: {default_project}")
            return default_project
        
        try:
            # Try to extract from various workflow fields
            project_sources = [
                ('metadata.project', workflow_data.get('metadata', {}).get('project')),
                ('spec.project', workflow_data.get('spec', {}).get('project')),
                ('identifier', workflow_data.get('identifier')),
            ]
            
            for source_name, project_value in project_sources:
                if project_value and isinstance(project_value, str):
                    # Clean up project name
                    if '___' in project_value:  # Likely the full project path
                        self.logger.debug(f"Extracted project from {source_name}: {project_value}")
                        return project_value
            
            self.logger.warning(f"Could not extract project from workflow, using default: {default_project}")
            return default_project
        
        except Exception as e:
            self.logger.error(f"Failed to extract project from workflow: {e}")
            return default_project
    
    def get_recommended_git_config(self) -> Dict[str, str]:
        """
        Get recommended Git configuration values
        
        Returns:
            Dictionary with recommended configuration
        """
        return {
            'git_username': 'harness',
            'products_repo_url': 'https://git.harness.io/JKARI3sqQ1aPpWL_nCe82w/CDK_Prod/Enterprise_IT___IOPS___Orchestration/iac_products_default_value.git',
            'overrides_repo_url': 'https://git.harness.io/JKARI3sqQ1aPpWL_nCe82w/CDK_Prod/Enterprise_IT___IOPS___Orchestration/iac_value_override.git',
            'project_name': 'Enterprise_IT___IOPS___Orchestration'
        }