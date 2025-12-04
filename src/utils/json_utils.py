"""
JSON utilities for parsing, validation, and manipulation
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union


class JSONUtils:
    """Utility functions for JSON operations"""
    
    @staticmethod
    def safe_parse(json_string: str, default: Any = None) -> Any:
        """
        Safely parse JSON string with error handling
        
        Args:
            json_string: JSON string to parse
            default: Default value to return on error
            
        Returns:
            Parsed JSON data or default value
        """
        logger = logging.getLogger(__name__)
        
        if not json_string or not isinstance(json_string, str):
            return default
        
        json_string = json_string.strip()
        if not json_string:
            return default or {}
        
        try:
            return json.loads(json_string)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parsing failed: {e}")
            logger.debug(f"Invalid JSON content: {json_string[:200]}...")
            return default
        except Exception as e:
            logger.error(f"Unexpected error parsing JSON: {e}")
            return default
    
    @staticmethod
    def safe_stringify(data: Any, indent: Optional[int] = None, 
                      separators: Optional[tuple] = (',', ':')) -> str:
        """
        Safely convert data to JSON string
        
        Args:
            data: Data to convert to JSON
            indent: JSON indentation (None for compact)
            separators: JSON separators tuple
            
        Returns:
            JSON string or empty string on error
        """
        logger = logging.getLogger(__name__)
        
        try:
            if data is None:
                return ""
            return json.dumps(data, indent=indent, separators=separators, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            logger.error(f"JSON serialization failed: {e}")
            return ""
        except Exception as e:
            logger.error(f"Unexpected error serializing JSON: {e}")
            return ""
    
    @staticmethod
    def validate_json_structure(data: Dict[str, Any], 
                              required_fields: List[str], 
                              optional_fields: List[str] = None) -> Dict[str, Any]:
        """
        Validate JSON structure against required and optional fields
        
        Args:
            data: JSON data to validate
            required_fields: List of required field names
            optional_fields: List of optional field names
            
        Returns:
            Validation results dictionary
        """
        result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'missing_required': [],
            'unexpected_fields': []
        }
        
        if not isinstance(data, dict):
            result['is_valid'] = False
            result['errors'].append("Data must be a dictionary")
            return result
        
        optional_fields = optional_fields or []
        expected_fields = set(required_fields + optional_fields)
        
        # Check required fields
        for field in required_fields:
            if field not in data:
                result['missing_required'].append(field)
                result['is_valid'] = False
        
        # Check for unexpected fields
        for field in data.keys():
            if field not in expected_fields:
                result['unexpected_fields'].append(field)
        
        if result['missing_required']:
            result['errors'].append(f"Missing required fields: {result['missing_required']}")
        
        if result['unexpected_fields']:
            result['warnings'].append(f"Unexpected fields found: {result['unexpected_fields']}")
        
        return result
    
    @staticmethod
    def deep_merge(base_dict: Dict[str, Any], update_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep merge two dictionaries
        
        Args:
            base_dict: Base dictionary
            update_dict: Dictionary with updates (takes precedence)
            
        Returns:
            Merged dictionary
        """
        from copy import deepcopy
        
        if not isinstance(base_dict, dict) or not isinstance(update_dict, dict):
            return update_dict if update_dict is not None else base_dict
        
        result = deepcopy(base_dict)
        
        for key, value in update_dict.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = JSONUtils.deep_merge(result[key], value)
            else:
                result[key] = deepcopy(value)
        
        return result
    
    @staticmethod
    def extract_nested_value(data: Dict[str, Any], path: str, 
                           default: Any = None, separator: str = '.') -> Any:
        """
        Extract nested value using dot notation
        
        Args:
            data: Dictionary to extract from
            path: Dot-separated path (e.g., "metadata.project.name")
            default: Default value if path not found
            separator: Path separator character
            
        Returns:
            Extracted value or default
        """
        if not isinstance(data, dict) or not path:
            return default
        
        keys = path.split(separator)
        current = data
        
        try:
            for key in keys:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return default
            return current
        except (KeyError, TypeError):
            return default
    
    @staticmethod
    def flatten_dict(data: Dict[str, Any], separator: str = '.', 
                    prefix: str = '') -> Dict[str, Any]:
        """
        Flatten nested dictionary to dot notation keys
        
        Args:
            data: Dictionary to flatten
            separator: Separator for nested keys
            prefix: Prefix for keys
            
        Returns:
            Flattened dictionary
        """
        result = {}
        
        if not isinstance(data, dict):
            return {prefix: data} if prefix else {}
        
        for key, value in data.items():
            new_key = f"{prefix}{separator}{key}" if prefix else key
            
            if isinstance(value, dict):
                result.update(JSONUtils.flatten_dict(value, separator, new_key))
            elif isinstance(value, list):
                result[new_key] = value
            else:
                result[new_key] = value
        
        return result
    
    @staticmethod
    def compare_json_objects(obj1: Any, obj2: Any, path: str = '') -> List[str]:
        """
        Compare two JSON objects and return list of differences
        
        Args:
            obj1: First object
            obj2: Second object
            path: Current path for nested comparison
            
        Returns:
            List of difference descriptions
        """
        differences = []
        
        if type(obj1) != type(obj2):
            differences.append(f"Type mismatch at {path or 'root'}: {type(obj1).__name__} vs {type(obj2).__name__}")
            return differences
        
        if isinstance(obj1, dict):
            # Check for keys only in obj1
            for key in obj1:
                if key not in obj2:
                    differences.append(f"Key '{key}' removed at {path}")
                else:
                    key_path = f"{path}.{key}" if path else key
                    differences.extend(JSONUtils.compare_json_objects(obj1[key], obj2[key], key_path))
            
            # Check for keys only in obj2
            for key in obj2:
                if key not in obj1:
                    differences.append(f"Key '{key}' added at {path}")
        
        elif isinstance(obj1, list):
            if len(obj1) != len(obj2):
                differences.append(f"List length changed at {path}: {len(obj1)} vs {len(obj2)}")
            
            for i, (item1, item2) in enumerate(zip(obj1, obj2)):
                item_path = f"{path}[{i}]" if path else f"[{i}]"
                differences.extend(JSONUtils.compare_json_objects(item1, item2, item_path))
        
        elif obj1 != obj2:
            differences.append(f"Value changed at {path or 'root'}: {obj1} -> {obj2}")
        
        return differences
    
    @staticmethod
    def sanitize_json_for_logging(data: Any, max_length: int = 500) -> str:
        """
        Sanitize JSON data for safe logging
        
        Args:
            data: Data to sanitize
            max_length: Maximum length of output string
            
        Returns:
            Sanitized string representation
        """
        try:
            json_str = JSONUtils.safe_stringify(data, indent=None)
            
            if len(json_str) <= max_length:
                return json_str
            
            # Truncate and add indicator
            return json_str[:max_length] + "... [truncated]"
        
        except Exception:
            return f"<{type(data).__name__} object>"