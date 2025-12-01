#!/usr/bin/env python3
"""
Harness Custom Drone Plugin
A robust, extensible plugin for Harness CI/CD pipelines with comprehensive error handling
and user-friendly configuration management.

Features:
- Flexible input handling (environment variables, command line args, config files)
- Comprehensive error handling and validation
- Structured output management
- Extensible action processing
- Detailed logging and debugging
"""

import json
import logging
import os
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional


class LogLevel(Enum):
    """Available logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class ActionType(Enum):
    """Supported action types."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


@dataclass
class PluginConfig:
    """Configuration for the drone plugin."""
    action: ActionType
    log_level: LogLevel = LogLevel.INFO
    debug_mode: bool = False
    dry_run: bool = False
    timeout: int = 300
    retry_attempts: int = 3
    
    # Action-specific configurations
    resource_config: Dict[str, Any] = field(default_factory=dict)
    deployment_name: Optional[str] = None
    user_defined_name: Optional[str] = None
    execution_id: Optional[str] = None
    triggered_by_email: Optional[str] = None
    primary_owner: Optional[str] = None
    component_name: Optional[str] = None


class PluginError(Exception):
    """Custom exception for plugin errors."""
    pass


class ValidationError(PluginError):
    """Raised when input validation fails."""
    pass


class ConfigurationError(PluginError):
    """Raised when configuration is invalid."""
    pass


class OutputManager:
    """Manages output to environment variables and optionally to drone output file."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.outputs: Dict[str, str] = {}
        
    def add_output(self, key: str, value: str) -> None:
        """Add an output variable."""
        try:
            if not key or not isinstance(key, str):
                raise ValueError("Output key must be a non-empty string")
            if not isinstance(value, str):
                value = str(value)
                
            self.outputs[key] = value
            
            # Set environment variable
            os.environ[key] = value
            self.logger.info(f"📝 Environment Variable Set: {key}={value[:50]}{'...' if len(value) > 50 else ''}")
                
        except Exception as e:
            self.logger.error(f"Failed to add output {key}: {e}")
            raise PluginError(f"Failed to add output {key}: {e}")
    
    def write_outputs(self) -> None:
        """Write all outputs to drone output file if available (for debugging)."""
        if not self.outputs:
            self.logger.info("No outputs to write")
            return
            
        # Write to drone output file if available (debugging only)
        drone_output_file = os.environ.get('DRONE_OUTPUT')
        if drone_output_file:
            try:
                Path(drone_output_file).parent.mkdir(parents=True, exist_ok=True)
                
                with open(drone_output_file, 'a') as f:
                    for key, value in self.outputs.items():
                        f.write(f"{key}={value}\n")
                self.logger.debug(f"✅ Debug: Wrote {len(self.outputs)} outputs to {drone_output_file}")
                
            except Exception as e:
                self.logger.debug(f"Debug: Failed to write to DRONE_OUTPUT file {drone_output_file}: {e}")
                # Don't raise exception for debug file write failures
        
        self.logger.info(f"🎯 Generated {len(self.outputs)} output variables")
    
    def get_summary(self) -> Dict[str, str]:
        """Get a summary of all outputs."""
        return self.outputs.copy()


class ConfigLoader:
    """Loads configuration from various sources with priority handling."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        
    def load_config(self) -> PluginConfig:
        """Load configuration from environment variables."""
        try:
            # Load from environment variables only
            config_data = self._load_from_env()
            
            # Create and validate configuration
            return self._create_config(config_data)
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            raise ConfigurationError(f"Configuration loading failed: {e}")
    
    def _load_from_env(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        env_mapping = {
            'PLUGIN_ACTION': 'action',
            'PLUGIN_LOG_LEVEL': 'log_level',
            'PLUGIN_DEBUG_MODE': 'debug_mode',
            'PLUGIN_DRY_RUN': 'dry_run',
            'PLUGIN_TIMEOUT': 'timeout',
            'PLUGIN_RETRY_ATTEMPTS': 'retry_attempts',
            'PLUGIN_DEPLOYMENT_NAME': 'deployment_name',
            'PLUGIN_USER_DEFINED_NAME': 'user_defined_name',
            'PLUGIN_EXECUTION_ID': 'execution_id',
            'PLUGIN_TRIGGERED_BY_EMAIL': 'triggered_by_email',
            'PLUGIN_PRIMARY_OWNER': 'primary_owner',
            'PLUGIN_COMPONENT_NAME': 'component_name',
            'PLUGIN_RESOURCE_CONFIG': 'resource_config'
        }
        
        config_data = {}
        for env_key, config_key in env_mapping.items():
            value = os.environ.get(env_key)
            if value:
                # Handle special cases
                if config_key in ['debug_mode', 'dry_run']:
                    config_data[config_key] = value.lower() in ['true', '1', 'yes', 'on']
                elif config_key in ['timeout', 'retry_attempts']:
                    try:
                        config_data[config_key] = int(value)
                    except ValueError:
                        self.logger.warning(f"Invalid integer value for {config_key}: {value}")
                elif config_key == 'resource_config':
                    config_data[config_key] = self._safe_json_parse(value, config_key)
                else:
                    config_data[config_key] = value
        
        return config_data
    
    def _create_config(self, config_data: Dict[str, Any]) -> PluginConfig:
        """Create PluginConfig from configuration data."""
        # Handle action type conversion
        action_str = config_data.get('action', '').lower()
        try:
            action = ActionType(action_str)
        except ValueError:
            raise ValidationError(f"Invalid action type: {action_str}. Supported: {[a.value for a in ActionType]}")
        
        # Handle log level conversion
        log_level_str = config_data.get('log_level', 'INFO').upper()
        try:
            log_level = LogLevel(log_level_str)
        except ValueError:
            self.logger.warning(f"Invalid log level: {log_level_str}, using INFO")
            log_level = LogLevel.INFO
        
        return PluginConfig(
            action=action,
            log_level=log_level,
            debug_mode=config_data.get('debug_mode', False),
            dry_run=config_data.get('dry_run', False),
            timeout=config_data.get('timeout', 300),
            retry_attempts=config_data.get('retry_attempts', 3),
            resource_config=config_data.get('resource_config', {}),
            deployment_name=config_data.get('deployment_name'),
            user_defined_name=config_data.get('user_defined_name'),
            execution_id=config_data.get('execution_id'),
            triggered_by_email=config_data.get('triggered_by_email'),
            primary_owner=config_data.get('primary_owner'),
            component_name=config_data.get('component_name')
        )
    
    def _safe_json_parse(self, json_str: str, config_name: str) -> Dict[str, Any]:
        """Safely parse JSON string with error handling."""
        if not json_str or json_str.strip() == '':
            return {}
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse {config_name}: {e}")
            self.logger.error(f"Invalid JSON content: {json_str[:200]}...")
            return {}


class ActionProcessor(ABC):
    """Abstract base class for action processors."""
    
    def __init__(self, config: PluginConfig, output_manager: OutputManager, logger: logging.Logger):
        self.config = config
        self.output_manager = output_manager
        self.logger = logger
    
    @abstractmethod
    def validate_inputs(self) -> None:
        """Validate inputs specific to this action type."""
        pass
    
    @abstractmethod
    def process(self) -> None:
        """Process the action."""
        pass


class CreateActionProcessor(ActionProcessor):
    """Processes create actions."""
    
    def validate_inputs(self) -> None:
        """Validate inputs for create action."""
        if not self.config.triggered_by_email:
            raise ValidationError("triggered_by_email is required for create action")
        if not self.config.execution_id:
            raise ValidationError("execution_id is required for create action")
    
    def process(self) -> None:
        """Process create action."""
        self.logger.info("🔨 Starting CREATE action processing...")
        
        # Generate deployment name
        deployment_name = self._generate_deployment_name()
        
        # Generate user-defined deployment name
        user_defined_deployment_name = self._process_user_defined_name()
        
        # Set resource owner
        resource_owner = f"user:account/{self.config.triggered_by_email}"
        
        # Process resource configuration
        item_map, workspace_ids = self._process_resource_config(deployment_name, resource_owner)
        
        # Export variables
        self.output_manager.add_output('RESOURCE_OWNER', resource_owner)
        self.output_manager.add_output('DEPLOYMENT_NAME', deployment_name)
        self.output_manager.add_output('USER_DEFINED_DEPLOYMENT_NAME', user_defined_deployment_name)
        self.output_manager.add_output('item_map', json.dumps(item_map, separators=(',', ':')))
        self.output_manager.add_output('workspace_ids', workspace_ids)
        
        self.logger.info(f"📦 Final Deployment Name: {deployment_name}")
        self.logger.info(f"🔗 Workspace IDs: {workspace_ids}")
    
    def _generate_deployment_name(self) -> str:
        """Generate deployment name from execution ID."""
        if not self.config.execution_id:
            raise ValidationError("Execution ID required for deployment name generation")
        
        deployment_name = f"deployment_{self.config.execution_id.lower().replace('-', '_')}"
        self.logger.info(f"🏷️  Generated deployment name: {deployment_name}")
        return deployment_name
    
    def _process_user_defined_name(self) -> str:
        """Process user-defined deployment name."""
        if not self.config.user_defined_name:
            return ""
        
        processed_name = self.config.user_defined_name.lower().replace(' ', '_').replace('-', '_')
        self.logger.info(f"👤 User-defined deployment name: {processed_name}")
        return processed_name
    
    def _process_resource_config(self, deployment_name: str, resource_owner: str) -> tuple:
        """Process resource configuration and generate item map."""
        entries = self.config.resource_config.get('entries', [])
        self.logger.info(f"📋 Processing {len(entries)} resource configuration entries...")
        
        if not entries:
            self.logger.warning("⚠️  No entries found in resource configuration - generating empty workspace")
            return [], ""
        
        item_map = []
        workspace_keys = []
        
        for idx, entry in enumerate(entries):
            try:
                entry_type = entry.get('type', '')
                resource_name = entry.get('resource_name', '')
                
                if not entry_type or not resource_name:
                    self.logger.warning(f"⚠️  Entry {idx + 1}: Skipping - missing required 'type' or 'resource_name' fields")
                    continue
                
                workspace_key = f"{entry_type}-{resource_name}-{deployment_name}"
                
                enhanced_entry = {
                    **entry,
                    'cdk_deployment_owner': resource_owner,
                    'cdk_deployment_id': deployment_name
                }
                
                item_map.append({workspace_key: enhanced_entry})
                workspace_keys.append(workspace_key)
                self.logger.info(f"✨ Entry {idx + 1}/{len(entries)}: Created workspace '{workspace_key}'")
                
            except Exception as e:
                self.logger.error(f"❌ Error processing entry {idx + 1}: {e}")
                if not self.config.debug_mode:
                    raise PluginError(f"Failed to process resource entry {idx}: {e}")
        
        return item_map, ','.join(workspace_keys)


class OtherActionProcessor(ActionProcessor):
    """Processes non-create actions."""
    
    def validate_inputs(self) -> None:
        """Validate inputs for non-create actions."""
        if not self.config.primary_owner:
            raise ValidationError(f"primary_owner is required for {self.config.action.value} action")
        if not self.config.deployment_name:
            raise ValidationError(f"deployment_name is required for {self.config.action.value} action")
    
    def process(self) -> None:
        """Process non-create action."""
        self.logger.info(f"🔄 Starting {self.config.action.value.upper()} action processing...")
        
        # Process deployment name
        deployment_name_processed = self.config.deployment_name.lower().replace('-', '_')
        
        # Prepare resource config
        resource_config_json = json.dumps(self.config.resource_config, separators=(',', ':'))
        
        # Export variables
        self.output_manager.add_output('RESOURCE_OWNER', self.config.primary_owner)
        self.output_manager.add_output('RESOURCE_CONFIG', resource_config_json)
        self.output_manager.add_output('DEPLOYMENT_NAME', deployment_name_processed)
        self.output_manager.add_output('workspace_ids', self.config.component_name or '')
        
        self.logger.info(f"👤 Resource Owner: {self.config.primary_owner}")
        self.logger.info(f"📦 Deployment Name: {deployment_name_processed}")
        self.logger.info(f"🔗 Workspace IDs: {self.config.component_name or 'None specified'}")


class DronePlugin:
    """Main plugin class that orchestrates the entire process."""
    
    def __init__(self):
        self.logger = None
        self.config = None
        self.output_manager = None
        self.action_processor = None
    
    def setup_logging(self, log_level: LogLevel, debug_mode: bool = False) -> None:
        """Setup logging configuration with color coding."""
        level = getattr(logging, log_level.value)
        
        # Create custom colored formatter
        class ColoredFormatter(logging.Formatter):
            # ANSI color codes
            COLORS = {
                'DEBUG': '\033[36m',    # Cyan
                'INFO': '\033[32m',     # Green
                'WARNING': '\033[33m',  # Yellow
                'ERROR': '\033[31m',    # Red
                'CRITICAL': '\033[35m', # Magenta
            }
            RESET = '\033[0m'
            BOLD = '\033[1m'
            
            def format(self, record):
                # Get color for log level
                color = self.COLORS.get(record.levelname, self.RESET)
                
                # Format timestamp
                if debug_mode:
                    timestamp = self.formatTime(record, '%Y-%m-%d %H:%M:%S')
                    log_format = f'{color}[{timestamp}] [{record.levelname:<8}] [{record.funcName}:{record.lineno}]{self.RESET} {record.getMessage()}'
                else:
                    timestamp = self.formatTime(record, '%H:%M:%S')
                    log_format = f'{color}[{timestamp}] [{record.levelname}]{self.RESET} {record.getMessage()}'
                
                return log_format
        
        # Setup handler with colored formatter
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(ColoredFormatter())
        
        # Configure root logger
        logging.basicConfig(
            level=level,
            handlers=[handler],
            force=True
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"🚀 Harness Drone Plugin initialized - Log Level: {log_level.value.upper()}")
    
    def load_configuration(self) -> None:
        """Load and validate configuration from environment variables."""
        config_loader = ConfigLoader(self.logger)
        self.config = config_loader.load_config()
        
        # Setup logging with loaded config
        if not self.logger:
            self.setup_logging(self.config.log_level, self.config.debug_mode)
        
        self.logger.info(f"⚙️  Configuration loaded successfully - Action: {self.config.action.value.upper()}")
    
    def initialize_components(self) -> None:
        """Initialize plugin components."""
        # Initialize output manager
        self.output_manager = OutputManager(logger=self.logger)
        
        # Initialize action processor
        if self.config.action == ActionType.CREATE:
            self.action_processor = CreateActionProcessor(self.config, self.output_manager, self.logger)
        elif self.config.action in [ActionType.UPDATE, ActionType.DELETE]:
            self.action_processor = OtherActionProcessor(self.config, self.output_manager, self.logger)
        else:
            raise ConfigurationError(f"Unsupported action: {self.config.action.value}")
    
    def validate_configuration(self) -> None:
        """Validate the loaded configuration."""
        if not self.config:
            raise ConfigurationError("Configuration not loaded")
        
        self.logger.debug("Validating configuration...")
        
        # Validate required PLUGIN_RESOURCE_CONFIG
        if not self.config.resource_config:
            raise ValidationError("PLUGIN_RESOURCE_CONFIG is required and cannot be empty")
        
        # Validate resource config structure
        if not isinstance(self.config.resource_config, dict):
            raise ValidationError("PLUGIN_RESOURCE_CONFIG must be valid JSON")
        
        # Validate action-specific inputs
        self.action_processor.validate_inputs()
        
        self.logger.info("✅ Configuration validation completed successfully")
    
    def execute_action(self) -> None:
        """Execute the configured action."""
        if self.config.dry_run:
            self.logger.info("🧪 DRY RUN MODE ENABLED - No actual changes will be made")
            return
        
        retry_count = 0
        while retry_count <= self.config.retry_attempts:
            try:
                self.action_processor.process()
                break
            except Exception as e:
                retry_count += 1
                if retry_count > self.config.retry_attempts:
                    raise
                self.logger.warning(f"🔄 Attempt {retry_count}/{self.config.retry_attempts} failed: {e}. Retrying...")
    
    def finalize_outputs(self) -> None:
        """Finalize and write all outputs."""
        try:
            self.output_manager.write_outputs()
            
            # Log summary
            outputs = self.output_manager.get_summary()
            self.logger.info(f"🎯 Plugin execution completed successfully with {len(outputs)} outputs generated")
            
            if self.config.debug_mode:
                for key, value in outputs.items():
                    self.logger.debug(f"📋 Output Variable: {key}={value}")
                    
        except Exception as e:
            self.logger.error(f"Failed to finalize outputs: {e}")
            raise
    
    def run(self) -> int:
        """Main execution method."""
        try:
            # Load configuration from environment variables
            self.load_configuration()
            
            self.logger.info("" + "=" * 70)
            self.logger.info("🚀 HARNESS CUSTOM DRONE PLUGIN - EXECUTION STARTED")
            self.logger.info("" + "=" * 70)
            
            # Initialize components
            self.initialize_components()
            
            # Validate configuration
            self.validate_configuration()
            
            # Execute action
            self.execute_action()
            
            # Finalize outputs
            self.finalize_outputs()
            
            self.logger.info("" + "=" * 70)
            self.logger.info("🎉 PLUGIN EXECUTION COMPLETED SUCCESSFULLY")
            self.logger.info("" + "=" * 70)
            
            return 0
            
        except KeyboardInterrupt:
            if self.logger:
                self.logger.warning("⚠️  Plugin execution interrupted by user (Ctrl+C)")
            return 130
        except ValidationError as e:
            if self.logger:
                self.logger.error(f"Validation error: {e}")
            else:
                print(f"Validation error: {e}", file=sys.stderr)
            return 2
        except ConfigurationError as e:
            if self.logger:
                self.logger.error(f"Configuration error: {e}")
            else:
                print(f"Configuration error: {e}", file=sys.stderr)
            return 3
        except PluginError as e:
            if self.logger:
                self.logger.error(f"Plugin error: {e}")
            else:
                print(f"Plugin error: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            if self.logger:
                self.logger.error(f"Unexpected error: {e}", exc_info=True)
            else:
                print(f"Unexpected error: {e}", file=sys.stderr)
            return 1




def main():
    """Main entry point - environment variables only mode."""
    try:
        # Create and run plugin using environment variables only
        plugin = DronePlugin()
        return plugin.run()
        
    except Exception as e:
        print(f"💥 Execution failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())