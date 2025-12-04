"""
Variable merging logic with priority handling
"""

import logging
from typing import Dict, Any, List, Union
from copy import deepcopy


class VariableMerger:
    """Handles merging of variables with priority resolution"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def merge_variables(self, lower_priority: Dict[str, Any], 
                       higher_priority: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge two variable dictionaries with higher_priority taking precedence
        
        Args:
            lower_priority: Variables with lower priority (base/defaults)
            higher_priority: Variables with higher priority (overrides/UI)
            
        Returns:
            Merged variables dictionary
        """
        if not lower_priority:
            return deepcopy(higher_priority) if higher_priority else {}
        
        if not higher_priority:
            return deepcopy(lower_priority) if lower_priority else {}
        
        result = deepcopy(lower_priority)
        
        for key, higher_value in higher_priority.items():
            if key not in result:
                # New key from higher priority
                result[key] = deepcopy(higher_value)
                self.logger.debug(f"Added new key '{key}' from higher priority")
            else:
                lower_value = result[key]
                merged_value = self._merge_values(lower_value, higher_value, key)
                result[key] = merged_value
        
        return result
    
    def _merge_values(self, lower_value: Any, higher_value: Any, key: str) -> Any:
        """
        Merge individual values based on their types
        
        Args:
            lower_value: Value from lower priority source
            higher_value: Value from higher priority source
            key: The key being merged (for logging)
            
        Returns:
            Merged value
        """
        # Handle None values
        if higher_value is None:
            return lower_value
        if lower_value is None:
            return higher_value
        
        # If both are lists, merge them
        if isinstance(lower_value, list) and isinstance(higher_value, list):
            return self._merge_lists(lower_value, higher_value, key)
        
        # If both are dictionaries, merge them recursively
        if isinstance(lower_value, dict) and isinstance(higher_value, dict):
            return self._merge_dictionaries(lower_value, higher_value, key)
        
        # For primitive types (str, int, bool, float), higher priority wins
        self.logger.debug(f"Key '{key}': higher priority value '{higher_value}' overwrites '{lower_value}'")
        return higher_value
    
    def _merge_lists(self, lower_list: List[Any], higher_list: List[Any], key: str) -> List[Any]:
        """
        Merge two lists based on the key type
        
        Args:
            lower_list: List from lower priority source
            higher_list: List from higher priority source
            key: The key being merged
            
        Returns:
            Merged list
        """
        # Special handling for tags (list of key-value objects)
        if key in ['additional_tags', 'tags'] and self._is_tag_list(higher_list):
            return self._merge_tag_lists(lower_list, higher_list)
        
        # For other lists, combine them with higher priority list taking precedence
        # Remove duplicates while preserving order
        result = deepcopy(higher_list)
        
        for lower_item in lower_list:
            if lower_item not in result:
                result.append(lower_item)
        
        self.logger.debug(f"Merged list '{key}': {len(lower_list)} + {len(higher_list)} -> {len(result)} items")
        return result
    
    def _merge_tag_lists(self, lower_tags: List[Dict[str, str]], 
                        higher_tags: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Merge tag lists where higher priority tags with same key override lower priority ones
        
        Args:
            lower_tags: Tags from lower priority source
            higher_tags: Tags from higher priority source
            
        Returns:
            Merged tag list
        """
        # Create lookup for higher priority tags
        higher_tag_keys = {tag.get('key'): tag for tag in higher_tags if 'key' in tag}
        
        # Start with higher priority tags
        result = deepcopy(higher_tags)
        
        # Add lower priority tags that don't conflict
        for lower_tag in lower_tags:
            if 'key' in lower_tag:
                tag_key = lower_tag['key']
                if tag_key not in higher_tag_keys:
                    result.append(deepcopy(lower_tag))
                    self.logger.debug(f"Added tag from defaults: {tag_key}={lower_tag.get('value', '')}")
                else:
                    self.logger.debug(f"Tag '{tag_key}' overridden by higher priority")
        
        return result
    
    def _merge_dictionaries(self, lower_dict: Dict[str, Any], 
                           higher_dict: Dict[str, Any], key: str) -> Dict[str, Any]:
        """
        Recursively merge two dictionaries
        
        Args:
            lower_dict: Dictionary from lower priority source
            higher_dict: Dictionary from higher priority source
            key: The key being merged
            
        Returns:
            Merged dictionary
        """
        result = deepcopy(lower_dict)
        
        for nested_key, nested_higher_value in higher_dict.items():
            if nested_key not in result:
                result[nested_key] = deepcopy(nested_higher_value)
            else:
                nested_lower_value = result[nested_key]
                result[nested_key] = self._merge_values(
                    nested_lower_value, nested_higher_value, f"{key}.{nested_key}"
                )
        
        return result
    
    def _is_tag_list(self, items: List[Any]) -> bool:
        """
        Check if a list represents tags (list of dicts with 'key' field)
        
        Args:
            items: List to check
            
        Returns:
            True if it looks like a tag list
        """
        return (
            isinstance(items, list) and 
            len(items) > 0 and 
            all(
                isinstance(item, dict) and 'key' in item 
                for item in items
            )
        )
    
    def apply_priority_chain(self, ui_variables: Dict[str, Any], 
                           priority_configs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Apply a chain of configurations in priority order
        
        Args:
            ui_variables: Original UI variables (lowest priority)
            priority_configs: List of configurations in ascending priority order
            
        Returns:
            Final merged configuration
        """
        result = deepcopy(ui_variables)
        
        self.logger.info(f"🔗 Applying priority chain: UI + {len(priority_configs)} config layers")
        
        for i, config in enumerate(priority_configs):
            if config:  # Skip None/empty configs
                old_result = deepcopy(result)
                result = self.merge_variables(result, config)
                
                # Log changes
                changes = self._detect_changes(old_result, result)
                if changes:
                    self.logger.info(f"📝 Layer {i+1} applied {len(changes)} changes: {', '.join(changes)}")
                else:
                    self.logger.debug(f"📋 Layer {i+1} applied no changes")
        
        return result
    
    def _detect_changes(self, old_config: Dict[str, Any], new_config: Dict[str, Any]) -> List[str]:
        """
        Detect what changed between two configurations
        
        Args:
            old_config: Previous configuration
            new_config: New configuration
            
        Returns:
            List of changed keys
        """
        changes = []
        
        # Check for modified or added keys
        for key, new_value in new_config.items():
            if key not in old_config:
                changes.append(f"+{key}")
            elif old_config[key] != new_value:
                changes.append(f"~{key}")
        
        # Check for removed keys
        for key in old_config:
            if key not in new_config:
                changes.append(f"-{key}")
        
        return changes