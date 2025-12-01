#!/usr/bin/env python3
"""
Harness Pipeline Preparation Script
Handles resource configuration and deployment preparation based on action type.
Uses Harness expression syntax directly.
"""

import json
import logging
import os
import sys
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def safe_json_parse(json_str: str, config_name: str) -> Dict[str, Any]:
    """
    Safely parse JSON string with error handling.
    
    Args:
        json_str: JSON string to parse
        config_name: Name of the configuration for logging
        
    Returns:
        Parsed JSON dictionary or empty dict on error
    """
    try:
        if not json_str or json_str.strip() == '':
            logger.warning(f"{config_name} is empty")
            return {}
        config = json.loads(json_str)
        logger.info(f"Successfully parsed {config_name}")
        return config
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse {config_name}: {e}")
        logger.error(f"Invalid JSON content: {json_str[:200]}...")
        raise ValueError(f"Invalid JSON in {config_name}: {e}")


def export_env_var(key: str, value: str) -> None:
    """
    Set environment variable similar to shell export and optionally append to DRONE_OUTPUT.
    """
    try:
        # Set environment variable
        os.environ[key] = value
        logger.info(f"Set environment variable: {key}={value}")

        # Append to DRONE_OUTPUT if available
        drone_output_file = os.environ.get('DRONE_OUTPUT')

        if drone_output_file:
            try:
                with open(drone_output_file, 'a') as f:
                    f.write(f"{key}={value}\n")
                logger.debug(f"DRONE_OUTPUT appended: {key}={value}")
            except Exception as e:
                logger.error(f"Failed writing {key} to DRONE_OUTPUT: {e}")

    except Exception as e:
        logger.error(f"Failed setting environment variable {key}: {e}")


def process_create_action(action: str, triggered_by_email: str, execution_id: str, 
                          user_defined_name: str, resource_config_str: str) -> None:
    """
    Process 'create' action workflow.
    
    Args:
        action: Pipeline action
        triggered_by_email: Email of user who triggered the pipeline
        execution_id: Pipeline execution ID
        user_defined_name: User-defined deployment name
        resource_config_str: JSON string of resource configuration
    """
    logger.info("=" * 60)
    logger.info("Processing 'create' action")
    logger.info("=" * 60)
    
    try:
        # Validate inputs
        if not triggered_by_email:
            raise ValueError("Triggered by email is required for 'create' action")
        if not execution_id:
            raise ValueError("Execution ID is required for 'create' action")
        
        # Generate deployment name
        deployment_name = f"deployment_{execution_id.lower().replace('-', '_')}"
        logger.info(f"Generated deployment name: {deployment_name}")
        
        # Generate user-defined deployment name
        user_defined_deployment_name = user_defined_name.lower().replace(' ', '_').replace('-', '_')
        if user_defined_deployment_name:
            logger.info(f"User-defined deployment name: {user_defined_deployment_name}")
        
        # Set resource owner
        resource_owner = f"user:account/{triggered_by_email}"
        logger.info(f"Resource owner: {resource_owner}")
        
        # Parse resource configuration
        resource_config = safe_json_parse(resource_config_str, "resource configuration")
        
        # Process entries and create item map
        entries = resource_config.get('entries', [])
        logger.info(f"Found {len(entries)} entries in resource configuration")
        
        if not entries:
            logger.warning("No entries found in resource configuration")
            item_map = []
            workspace_ids = ""
        else:
            item_map = []
            workspace_keys = []
            
            for idx, entry in enumerate(entries):
                entry_type = entry.get('type', '')
                resource_name = entry.get('resource_name', '')
                
                if not entry_type or not resource_name:
                    logger.warning(f"Entry {idx}: Skipping entry with missing type or resource_name: {entry}")
                    continue
                
                workspace_key = f"{entry_type}-{resource_name}-{deployment_name}"
                
                # Add deployment metadata to entry
                enhanced_entry = {
                    **entry,
                    'cdk_deployment_owner': resource_owner,
                    'cdk_deployment_id': deployment_name
                }
                
                item_map.append({workspace_key: enhanced_entry})
                workspace_keys.append(workspace_key)
                logger.info(f"Entry {idx + 1}: Created workspace '{workspace_key}'")
            
            workspace_ids = ','.join(workspace_keys)
        
        # Convert item_map to JSON string (compact format)
        item_map_json = json.dumps(item_map, separators=(',', ':'))
        
        # Export environment variables
        logger.info("")
        logger.info("Exporting environment variables:")
        export_env_var('RESOURCE_OWNER', resource_owner)
        export_env_var('DEPLOYMENT_NAME', deployment_name)
        export_env_var('USER_DEFINED_DEPLOYMENT_NAME', user_defined_deployment_name)
        export_env_var('item_map', item_map_json)
        export_env_var('workspace_ids', workspace_ids)
        
        logger.info("")
        logger.info(f"Deployment Name: {deployment_name}")
        logger.info(f"Workspace IDs: {workspace_ids}")
        
    except Exception as e:
        logger.error(f"Error processing 'create' action: {e}", exc_info=True)
        raise


def process_other_action(action: str, primary_owner: str, deployment_name: str, 
                        component_name: str, resource_config_str: str) -> None:
    """
    Process non-create actions workflow.
    
    Args:
        action: Pipeline action
        primary_owner: Primary owner of the resource
        deployment_name: Name of the deployment
        component_name: Component name (workspace IDs)
        resource_config_str: JSON string of resource configuration
    """
    logger.info("=" * 60)
    logger.info(f"Processing '{action}' action")
    logger.info("=" * 60)
    
    try:
        # Validate inputs
        if not primary_owner:
            raise ValueError(f"Primary owner is required for '{action}' action")
        if not deployment_name:
            raise ValueError(f"Deployment name is required for '{action}' action")
        
        # Process deployment name
        deployment_name_processed = deployment_name.lower().replace('-', '_')
        logger.info(f"Processed deployment name: {deployment_name_processed}")
        
        # Parse and compact resource configuration
        resource_config = safe_json_parse(resource_config_str, "resource configuration")
        resource_config_json = json.dumps(resource_config, separators=(',', ':'))
        
        # Export environment variables
        logger.info("")
        logger.info("Exporting environment variables:")
        export_env_var('RESOURCE_OWNER', primary_owner)
        export_env_var('RESOURCE_CONFIG', resource_config_json)
        export_env_var('DEPLOYMENT_NAME', deployment_name_processed)
        export_env_var('workspace_ids', component_name)
        
        logger.info("")
        logger.info(f"Resource Owner: {primary_owner}")
        logger.info(f"Deployment Name: {deployment_name_processed}")
        logger.info(f"Workspace IDs: {component_name}")
        
    except Exception as e:
        logger.error(f"Error processing '{action}' action: {e}", exc_info=True)
        raise


def main():
    """Main execution function."""
    exit_code = 0
    
    try:        
        logger.info("=" * 60)
        logger.info("HARNESS PIPELINE PREPARATION SCRIPT")
        logger.info("=" * 60)
        
        # Read Harness pipeline variables using expression syntax
        # These will be replaced by Harness at runtime
        action = '<+pipeline.variables.action>'
        advanced_resource_config = '<+pipeline.variables.advanced_resourceConfig>'
        
        logger.info(f"Prep Stage - Action: {action}")
        
        # Log advanced resource config if available
        if advanced_resource_config and advanced_resource_config != '<+pipeline.variables.advanced_resourceConfig>':
            logger.info(f"Advanced Resource Config: {advanced_resource_config}")
        
        # Process based on action
        if action == "create":
            # Variables for 'create' action
            triggered_by_email = '<+pipeline.triggeredBy.email>'
            execution_id = '<+pipeline.executionId>'
            user_defined_name = '<+pipeline.variables.user_defined_deployment_name>'
            resource_config = '<+pipeline.variables.resourceConfig>'
            
            process_create_action(
                action=action,
                triggered_by_email=triggered_by_email,
                execution_id=execution_id,
                user_defined_name=user_defined_name,
                resource_config_str=resource_config
            )
        else:
            # Variables for other actions
            primary_owner = '<+pipeline.variables.primaryOwner>'
            deployment_name = '<+pipeline.variables.deployment_name>'
            component_name = '<+pipeline.variables.component_name>'
            resource_config = '<+pipeline.variables.resourceConfig>'
            
            process_other_action(
                action=action,
                primary_owner=primary_owner,
                deployment_name=deployment_name,
                component_name=component_name,
                resource_config_str=resource_config
            )
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("PREPARATION STAGE COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error("")
        logger.error("=" * 60)
        logger.error("FATAL ERROR IN PREPARATION STAGE")
        logger.error("=" * 60)
        logger.error(f"Error: {e}", exc_info=True)
        exit_code = 1
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())