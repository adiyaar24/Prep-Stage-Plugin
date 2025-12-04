"""
Enhanced plugin configuration with Git integration support
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EnhancedPluginConfig:
    """Extended configuration for Git-based default values"""
    
    # Git configuration
    git_username: Optional[str] = None
    git_token: Optional[str] = None
    
    # Repository URLs
    products_repo_url: str = "https://git.harness.io/JKARI3sqQ1aPpWL_nCe82w/CDK_Prod/Enterprise_IT___IOPS___Orchestration/iac_products_default_value.git"
    overrides_repo_url: str = "https://git.harness.io/JKARI3sqQ1aPpWL_nCe82w/CDK_Prod/Enterprise_IT___IOPS___Orchestration/iac_value_override.git"
    
    # Project configuration
    project_name: str = "Enterprise_IT___IOPS___Orchestration"
    cloud_project: Optional[str] = None
    
    # Repository management
    repo_work_dir: str = "."
    enable_git_integration: bool = True
    
    # Processing options
    skip_missing_defaults: bool = True
    validate_merged_config: bool = True
    log_variable_changes: bool = True
    
    @property
    def is_git_configured(self) -> bool:
        """Check if git integration is properly configured"""
        return bool(
            self.enable_git_integration and
            self.git_username and 
            self.git_token
        )
    
    @property 
    def products_repo_name(self) -> str:
        """Get local name for products repository"""
        return "iac_products_default_value"
    
    @property
    def overrides_repo_name(self) -> str:
        """Get local name for overrides repository"""
        return "iac_value_override"
    
    def get_environment_mapping(self) -> dict:
        """Get mapping of new environment variables"""
        return {
            'PLUGIN_GIT_USERNAME': 'git_username',
            'PLUGIN_GIT_TOKEN': 'git_token',
            'PLUGIN_PRODUCTS_REPO_URL': 'products_repo_url',
            'PLUGIN_OVERRIDES_REPO_URL': 'overrides_repo_url',
            'PLUGIN_PROJECT_NAME': 'project_name',
            'PLUGIN_CLOUD_PROJECT': 'cloud_project',
            'PLUGIN_REPO_WORK_DIR': 'repo_work_dir',
            'PLUGIN_ENABLE_GIT_INTEGRATION': 'enable_git_integration',
            'PLUGIN_SKIP_MISSING_DEFAULTS': 'skip_missing_defaults',
            'PLUGIN_VALIDATE_MERGED_CONFIG': 'validate_merged_config',
            'PLUGIN_LOG_VARIABLE_CHANGES': 'log_variable_changes'
        }