"""
Enhanced Harness Custom Drone Plugin with Git-based Default Values
This is the enhanced version that integrates Git repositories while maintaining
backward compatibility with the existing plugin.
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Import existing plugin components
from main import (
    DronePlugin as BaseDronePlugin,
    ConfigLoader,
    PluginConfig,
    ActionType,
    LogLevel,
    CreateActionProcessor,
    OtherActionProcessor,
    OutputManager,
    PluginError,
    ValidationError,
    ConfigurationError
)

# Import new Git integration components
from src.config import EnhancedPluginConfig
from src.defaults_processor import DefaultsProcessor


class EnhancedConfigLoader(ConfigLoader):
    """Enhanced config loader with Git integration support"""
    
    def _load_from_env(self) -> Dict[str, Any]:
        """Load configuration including Git settings"""
        # Get base configuration
        config_data = super()._load_from_env()
        
        # Add Git-specific environment variables
        enhanced_config = EnhancedPluginConfig()
        git_env_mapping = enhanced_config.get_environment_mapping()
        
        # Also check for Harness pipeline variables (without PLUGIN_ prefix)
        harness_mapping = {
            'GIT_USERNAME': 'git_username',
            'GIT_TOKEN': 'git_token', 
            'PROJECT_NAME': 'project_name',
            'CLOUD_PROJECT': 'cloud_project',
            'USE_ENHANCED': 'use_enhanced',
            'ENABLE_GIT_INTEGRATION': 'enable_git_integration',
            'SKIP_MISSING_DEFAULTS': 'skip_missing_defaults',
            'LOG_VARIABLE_CHANGES': 'log_variable_changes',
            'VALIDATE_MERGED_CONFIG': 'validate_merged_config',
            'PRODUCTS_REPO_URL': 'products_repo_url',
            'OVERRIDES_REPO_URL': 'overrides_repo_url',
            'REPO_WORK_DIR': 'repo_work_dir'
        }
        
        # Check both PLUGIN_ prefixed and direct environment variables
        all_mappings = {**git_env_mapping, **harness_mapping}
        
        for env_key, config_key in all_mappings.items():
            value = os.environ.get(env_key)
            if value:
                # Handle special cases
                if config_key in ['enable_git_integration', 'skip_missing_defaults', 
                                'validate_merged_config', 'log_variable_changes', 'use_enhanced']:
                    config_data[config_key] = value.lower() in ['true', '1', 'yes', 'on']
                else:
                    config_data[config_key] = value
        
        return config_data
    
    def _create_config(self, config_data: Dict[str, Any]) -> PluginConfig:
        """Create enhanced configuration"""
        # Create base config
        base_config = super()._create_config(config_data)
        
        # Add Git configuration attributes
        for attr_name in ['git_username', 'git_token', 'products_repo_url', 'overrides_repo_url',
                         'project_name', 'cloud_project', 'repo_work_dir', 
                         'enable_git_integration', 'skip_missing_defaults', 
                         'validate_merged_config', 'log_variable_changes', 'use_enhanced']:
            if hasattr(base_config, attr_name):
                continue  # Don't overwrite existing attributes
            setattr(base_config, attr_name, config_data.get(attr_name))
        
        return base_config


class EnhancedCreateActionProcessor(CreateActionProcessor):
    """Enhanced create processor with Git integration"""
    
    def __init__(self, config: PluginConfig, output_manager: OutputManager, 
                 logger: logging.Logger, defaults_processor: Optional[DefaultsProcessor] = None):
        super().__init__(config, output_manager, logger)
        self.defaults_processor = defaults_processor
    
    def process(self) -> None:
        """Enhanced process with Git-based defaults"""
        self.logger.info("🔨 Starting enhanced CREATE action processing...")
        
        # Extract and process resource configuration with Git defaults
        resource_config = self.config.resource_config
        entries = resource_config.get('entries', [])
        
        # Apply Git-based defaults if processor is available
        if self.defaults_processor:
            try:
                self.logger.info("🔗 Applying Git-based default values...")
                processed_entries = self.defaults_processor.process_resource_entries(entries)
                
                # Update the resource config with processed entries
                self.config.resource_config = {
                    **resource_config,
                    'entries': processed_entries
                }
                
                self.logger.info(f"✅ Applied Git-based defaults to {len(processed_entries)} entries")
                
                # Log the changes if enabled
                if getattr(self.config, 'log_variable_changes', True):
                    self._log_processing_changes(entries, processed_entries)
                
            except Exception as e:
                self.logger.error(f"Failed to apply Git-based defaults: {e}")
                if not getattr(self.config, 'skip_missing_defaults', True):
                    raise PluginError(f"Git defaults processing failed: {e}")
                else:
                    self.logger.warning("Continuing with original configuration due to skip_missing_defaults=True")
        
        # Continue with existing CREATE logic
        super().process()
    
    def _log_processing_changes(self, original_entries: list, processed_entries: list) -> None:
        """Log changes made during processing"""
        for i, (original, processed) in enumerate(zip(original_entries, processed_entries)):
            changes = self._detect_entry_changes(original, processed)
            if changes:
                self.logger.info(f"📝 Entry {i+1} changes: {', '.join(changes[:5])}" + 
                               (f" (+{len(changes)-5} more)" if len(changes) > 5 else ""))
    
    def _detect_entry_changes(self, original: Dict[str, Any], processed: Dict[str, Any]) -> list:
        """Detect changes between original and processed entries"""
        changes = []
        
        # Check for new/modified keys
        for key, value in processed.items():
            if key not in original:
                changes.append(f"+{key}")
            elif original[key] != value:
                changes.append(f"~{key}")
        
        return changes


class EnhancedOtherActionProcessor(OtherActionProcessor):
    """Enhanced update/delete processor with Git integration"""
    
    def __init__(self, config: PluginConfig, output_manager: OutputManager, 
                 logger: logging.Logger, defaults_processor: Optional[DefaultsProcessor] = None):
        super().__init__(config, output_manager, logger)
        self.defaults_processor = defaults_processor
    
    def process(self) -> None:
        """Enhanced process with Git-based defaults for update/delete"""
        self.logger.info(f"🔄 Starting enhanced {self.config.action.value.upper()} action processing...")
        
        # For update actions, we can apply defaults to help with configuration
        if (self.config.action == ActionType.UPDATE and 
            self.defaults_processor and 
            self.config.resource_config.get('entries')):
            
            try:
                entries = self.config.resource_config.get('entries', [])
                self.logger.info("🔗 Applying Git-based defaults to update configuration...")
                
                processed_entries = self.defaults_processor.process_resource_entries(entries)
                self.config.resource_config['entries'] = processed_entries
                
                self.logger.info(f"✅ Applied Git-based defaults to {len(processed_entries)} update entries")
                
            except Exception as e:
                self.logger.warning(f"Failed to apply defaults to update config: {e}")
        
        # Continue with existing logic
        super().process()


class EnhancedDronePlugin(BaseDronePlugin):
    """Enhanced drone plugin with Git integration"""
    
    def __init__(self):
        super().__init__()
        self.defaults_processor: Optional[DefaultsProcessor] = None
        self.enhanced_config: Optional[EnhancedPluginConfig] = None
    
    def load_configuration(self) -> None:
        """Load configuration with Git integration support"""
        # Use enhanced config loader
        config_loader = EnhancedConfigLoader(self.logger)
        self.config = config_loader.load_config()
        
        # Setup logging if not already done
        if not self.logger:
            self.setup_logging(self.config.log_level, self.config.debug_mode)
        
        # Create enhanced config for Git integration
        self.enhanced_config = EnhancedPluginConfig()
        
        # Copy values from main config to enhanced config
        for attr_name in ['git_username', 'git_token', 'project_name', 'cloud_project',
                         'enable_git_integration']:
            if hasattr(self.config, attr_name):
                setattr(self.enhanced_config, attr_name, getattr(self.config, attr_name))
        
        self.logger.info(f"⚙️  Enhanced configuration loaded - Action: {self.config.action.value.upper()}")
        
        # Log Git integration status
        if self.enhanced_config.is_git_configured:
            self.logger.info("🔗 Git integration enabled")
        else:
            self.logger.info("📋 Git integration disabled (no credentials provided)")
    
    def initialize_git_integration(self) -> None:
        """Initialize Git integration if configured"""
        if not self.enhanced_config.is_git_configured:
            self.logger.info("📋 Skipping Git integration (not configured)")
            return
        
        try:
            self.logger.info("🔗 Initializing Git integration...")
            
            # Initialize defaults processor
            self.defaults_processor = DefaultsProcessor(self.enhanced_config)
            
            # Setup repositories
            success = self.defaults_processor.setup_repositories()
            
            if success:
                self.logger.info("✅ Git integration initialized successfully")
                
                # Validate repositories if configured
                if getattr(self.enhanced_config, 'validate_merged_config', True):
                    validation = self.defaults_processor.validate_repositories()
                    if not validation['is_valid']:
                        self.logger.warning(f"Repository validation warnings: {validation.get('errors', [])}")
                    if validation.get('warnings'):
                        for warning in validation['warnings']:
                            self.logger.warning(f"Repo validation: {warning}")
            else:
                self.logger.error("❌ Failed to initialize Git integration")
                if not getattr(self.enhanced_config, 'skip_missing_defaults', True):
                    raise ConfigurationError("Git integration setup failed")
                else:
                    self.logger.warning("Continuing without Git integration")
                    self.defaults_processor = None
        
        except Exception as e:
            self.logger.error(f"Git integration initialization failed: {e}")
            if not getattr(self.enhanced_config, 'skip_missing_defaults', True):
                raise ConfigurationError(f"Git integration failed: {e}")
            else:
                self.logger.warning("Continuing without Git integration due to skip_missing_defaults=True")
                self.defaults_processor = None
    
    def initialize_components(self) -> None:
        """Initialize enhanced components with Git support"""
        # Initialize output manager
        self.output_manager = OutputManager(logger=self.logger)
        
        # Initialize enhanced action processors
        if self.config.action == ActionType.CREATE:
            self.action_processor = EnhancedCreateActionProcessor(
                self.config, self.output_manager, self.logger, self.defaults_processor
            )
        elif self.config.action in [ActionType.UPDATE, ActionType.DELETE]:
            self.action_processor = EnhancedOtherActionProcessor(
                self.config, self.output_manager, self.logger, self.defaults_processor
            )
        else:
            raise ConfigurationError(f"Unsupported action: {self.config.action.value}")
    
    def finalize_outputs(self) -> None:
        """Enhanced finalization with Git statistics"""
        try:
            # Add Git processing statistics to outputs
            if self.defaults_processor:
                git_stats = self.defaults_processor.get_processing_statistics()
                
                self.output_manager.add_output('gitIntegrationEnabled', str(git_stats['git_configured']))
                self.output_manager.add_output('repositoriesSetup', str(git_stats['repositories_setup']))
                
                # Cleanup
                self.defaults_processor.cleanup()
            
            # Call parent finalization
            super().finalize_outputs()
            
        except Exception as e:
            self.logger.error(f"Failed to finalize outputs: {e}")
            raise
    
    def run(self) -> int:
        """Enhanced run method with Git integration"""
        try:
            # Load configuration
            self.load_configuration()
            
            self.logger.info("=" * 70)
            self.logger.info("🚀 ENHANCED HARNESS DRONE PLUGIN - EXECUTION STARTED")
            self.logger.info("=" * 70)
            
            # Initialize Git integration first (if configured)
            self.initialize_git_integration()
            
            # Initialize components
            self.initialize_components()
            
            # Validate configuration
            self.validate_configuration()
            
            # Execute action
            self.execute_action()
            
            # Finalize outputs
            self.finalize_outputs()
            
            self.logger.info("=" * 70)
            self.logger.info("🎉 ENHANCED PLUGIN EXECUTION COMPLETED SUCCESSFULLY")
            self.logger.info("=" * 70)
            
            return 0
            
        except Exception as e:
            # Use parent error handling
            return super().run()


def main():
    """Main entry point for enhanced plugin"""
    try:
        # Check both PLUGIN_USE_ENHANCED and USE_ENHANCED environment variables
        use_enhanced = (
            os.environ.get('USE_ENHANCED', '').lower() in ['true', '1', 'yes', 'on'] or
            os.environ.get('PLUGIN_USE_ENHANCED', 'true').lower() in ['true', '1', 'yes', 'on']
        )
        
        if use_enhanced:
            plugin = EnhancedDronePlugin()
        else:
            # Fall back to original plugin
            from main import DronePlugin
            plugin = DronePlugin()
        
        return plugin.run()
        
    except Exception as e:
        print(f"💥 Enhanced execution failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())