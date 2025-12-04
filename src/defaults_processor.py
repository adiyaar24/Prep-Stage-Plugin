"""
Main defaults processor that coordinates all Git operations and variable merging
"""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from .git_integration import GitManager, FileLoader
from .defaults import ProductDefaultsLoader, OverrideManager, VariableMerger
from .config import EnhancedPluginConfig, GitConfiguration


class DefaultsProcessor:
    """Main processor for Git-based default values and overrides"""
    
    def __init__(self, config: EnhancedPluginConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.git_manager = None
        self.file_loader = FileLoader()
        self.product_loader = ProductDefaultsLoader(self.file_loader)
        self.override_manager = OverrideManager(self.file_loader)
        self.variable_merger = VariableMerger()
        self.git_config = GitConfiguration()
        
        # Repository paths
        self.products_repo_path: Optional[Path] = None
        self.overrides_repo_path: Optional[Path] = None
        
        # Initialize if configured
        if self.config.is_git_configured:
            self._initialize_git_components()
    
    def _initialize_git_components(self) -> bool:
        """Initialize Git-related components"""
        try:
            # Validate git configuration
            validation = self.git_config.validate_git_config(
                self.config.git_username,
                self.config.git_token,
                [self.config.products_repo_url, self.config.overrides_repo_url]
            )
            
            if not validation['is_valid']:
                self.logger.error(f"Git configuration validation failed: {validation['errors']}")
                return False
            
            if validation['warnings']:
                for warning in validation['warnings']:
                    self.logger.warning(f"Git config warning: {warning}")
            
            # Initialize components
            self.git_manager = GitManager(
                self.config.git_username,
                self.config.git_token,
                self.config.repo_work_dir
            )
            
            self.logger.info("✅ Git components initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Git components: {e}")
            return False
    
    def setup_repositories(self) -> bool:
        """Clone or update repositories"""
        if not self.git_manager:
            self.logger.warning("Git manager not initialized, skipping repository setup")
            return False
        
        try:
            self.logger.info("🔄 Setting up Git repositories...")
            
            # Setup products repository
            if not self._setup_repository(
                self.config.products_repo_url,
                self.config.products_repo_name,
                "products_repo_path"
            ):
                return False
            
            # Setup overrides repository  
            if not self._setup_repository(
                self.config.overrides_repo_url,
                self.config.overrides_repo_name,
                "overrides_repo_path"
            ):
                return False
            
            self.logger.info("✅ All repositories setup successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to setup repositories: {e}")
            return False
    
    def _setup_repository(self, repo_url: str, repo_name: str, path_attr: str) -> bool:
        """Setup a single repository"""
        try:
            # Clone repository (fresh clone each time)
            self.logger.info(f"🔄 Setting up repository: {repo_name}")
            repo_path = self.git_manager.clone_repository(repo_url, repo_name)
            
            setattr(self, path_attr, repo_path)
            self.logger.info(f"✅ Repository {repo_name} setup complete")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to setup repository {repo_name}: {e}")
            return False
    
    def process_resource_entries(self, resource_entries: List[Dict[str, Any]], 
                               cloud_project: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Process resource entries through the 6-touch priority system
        
        Args:
            resource_entries: List of resource entry dictionaries
            cloud_project: Cloud project name (optional, will try to extract)
            
        Returns:
            List of processed resource entries with merged defaults
        """
        if not resource_entries:
            self.logger.warning("No resource entries to process")
            return []
        
        if not self.config.is_git_configured:
            self.logger.warning("Git integration not configured, returning original entries")
            return resource_entries
        
        # Extract cloud project if not provided
        if not cloud_project:
            cloud_project = self._extract_cloud_project(resource_entries)
        
        self.logger.info(f"🔄 Processing {len(resource_entries)} resource entries with cloud project: {cloud_project}")
        
        processed_entries = []
        for i, entry in enumerate(resource_entries):
            try:
                processed_entry = self._process_single_entry(entry, cloud_project, i + 1)
                processed_entries.append(processed_entry)
            except Exception as e:
                self.logger.error(f"Failed to process entry {i + 1}: {e}")
                # Fall back to original entry
                processed_entries.append(entry)
        
        self.logger.info(f"✅ Processed {len(processed_entries)} resource entries")
        return processed_entries
    
    def _process_single_entry(self, entry: Dict[str, Any], cloud_project: Optional[str], 
                            entry_num: int) -> Dict[str, Any]:
        """Process a single resource entry through the priority chain"""
        
        # Extract resource information
        resource_type = entry.get('type')
        resource_name = entry.get('resource_name')
        environment = entry.get('env')
        
        if not all([resource_type, resource_name, environment]):
            self.logger.warning(f"Entry {entry_num}: Missing required fields (type/resource_name/env), skipping processing")
            return entry
        
        self.logger.info(f"🔄 Processing entry {entry_num}: {resource_type}/{resource_name} ({environment})")
        
        # 1st Touch: Start with UI values (entry as-is)
        result = entry.copy()
        
        # Load all configuration layers
        configs_to_apply = []
        
        try:
            # 2nd/3rd Touch: Product defaults (if repositories are setup)
            if self.products_repo_path:
                product_defaults = self.product_loader.load_defaults(
                    self.products_repo_path, self.config.project_name, resource_type, environment
                )
                if product_defaults:
                    configs_to_apply.append(product_defaults)
                    self.logger.debug(f"Entry {entry_num}: Loaded product defaults")
            
            # 4th Touch: Resource type enforced defaults
            if self.overrides_repo_path:
                enforced_defaults = self.override_manager.load_enforced_defaults(
                    self.overrides_repo_path, resource_type
                )
                if enforced_defaults:
                    configs_to_apply.append(enforced_defaults)
                    self.logger.debug(f"Entry {entry_num}: Loaded enforced defaults")
                
                # 5th Touch: Cloud project defaults
                if cloud_project:
                    cloud_defaults = self.override_manager.load_cloud_project_defaults(
                        self.overrides_repo_path, resource_type, cloud_project
                    )
                    if cloud_defaults:
                        configs_to_apply.append(cloud_defaults)
                        self.logger.debug(f"Entry {entry_num}: Loaded cloud project defaults")
                    
                    # 6th Touch: Specific resource overrides
                    resource_overrides = self.override_manager.load_resource_overrides(
                        self.overrides_repo_path, resource_type, cloud_project, resource_name
                    )
                    if resource_overrides:
                        configs_to_apply.append(resource_overrides)
                        self.logger.debug(f"Entry {entry_num}: Loaded resource overrides")
            
            # Apply all configurations in priority order
            if configs_to_apply:
                result = self.variable_merger.apply_priority_chain(result, configs_to_apply)
                self.logger.info(f"✅ Entry {entry_num}: Applied {len(configs_to_apply)} configuration layers")
            else:
                self.logger.warning(f"Entry {entry_num}: No additional configurations found")
        
        except Exception as e:
            self.logger.error(f"Entry {entry_num}: Failed to apply configurations: {e}")
            # Return original entry on error
            result = entry
        
        return result
    
    def _extract_cloud_project(self, resource_entries: List[Dict[str, Any]]) -> Optional[str]:
        """Extract cloud project from resource entries"""
        if not resource_entries:
            return None
        
        # Try configured cloud project first
        if self.config.cloud_project:
            return self.config.cloud_project
        
        # Extract from first entry
        first_entry = resource_entries[0]
        return self.git_config.extract_cloud_project_from_config({'entries': [first_entry]})
    
    def validate_repositories(self) -> Dict[str, Any]:
        """Validate repository structure and content"""
        validation_result = {
            'is_valid': True,
            'products_repo': {},
            'overrides_repo': {},
            'errors': [],
            'warnings': []
        }
        
        if not self.config.is_git_configured:
            validation_result['warnings'].append("Git integration not configured")
            return validation_result
        
        try:
            # Validate products repository
            if self.products_repo_path:
                validation_result['products_repo'] = self.product_loader.validate_defaults_structure(
                    self.products_repo_path, self.config.project_name
                )
                if not validation_result['products_repo']['is_valid']:
                    validation_result['is_valid'] = False
                    validation_result['errors'].extend([
                        f"Products repo: {error}" 
                        for error in validation_result['products_repo'].get('errors', [])
                    ])
            
            # Validate overrides repository
            if self.overrides_repo_path:
                validation_result['overrides_repo'] = self.override_manager.validate_override_structure(
                    self.overrides_repo_path
                )
                if not validation_result['overrides_repo']['is_valid']:
                    validation_result['is_valid'] = False
                    validation_result['errors'].extend([
                        f"Overrides repo: {error}"
                        for error in validation_result['overrides_repo'].get('errors', [])
                    ])
        
        except Exception as e:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"Validation failed: {e}")
        
        return validation_result
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get statistics about processing and repositories"""
        stats = {
            'git_configured': self.config.is_git_configured,
            'repositories_setup': bool(self.products_repo_path and self.overrides_repo_path),
            'repository_info': {}
        }
        
        if self.git_manager:
            if self.products_repo_path:
                stats['repository_info']['products'] = self.git_manager.get_repository_info(self.products_repo_path)
            if self.overrides_repo_path:
                stats['repository_info']['overrides'] = self.git_manager.get_repository_info(self.overrides_repo_path)
        
        return stats
    
    def cleanup(self) -> None:
        """Cleanup resources"""
        try:
            if self.git_manager:
                # Clean up specific repository directories
                repo_names = [
                    self.config.products_repo_name,
                    self.config.overrides_repo_name
                ]
                self.git_manager.cleanup_repositories(repo_names)
            
            self.logger.debug("🧹 Cleanup completed")
        
        except Exception as e:
            self.logger.warning(f"Cleanup failed: {e}")