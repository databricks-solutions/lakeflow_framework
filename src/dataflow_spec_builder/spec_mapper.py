import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Tuple, Optional, Any

from constants import FrameworkPaths
import pipeline_config
import utility


class SpecMapper:
    """
    Handles dataflow spec version migrations and key mappings.
    
    Supports operations:
    - move: Move a key to a new location
    - rename_all: Rename keys recursively throughout the spec
    - rename_specific: Rename specific keys at exact paths
    - delete: Delete keys from the spec
    
    Each operation supports conditional execution based on spec properties.
    """
    
    class Keys:
        """Constants for spec mapping keys."""
        DATA = "data"
        DATA_FLOW_ID = "dataFlowId"
        DATA_FLOW_TYPE = "dataFlowType"
        DATA_FLOW_VERSION = "dataFlowVersion"
        GLOBAL = "global"
    
    class Operators:
        """Constants for condition operators."""
        EQUAL_TO = "equal_to"
        NOT_EQUAL_TO = "not_equal_to"
        IN = "in"
        NOT_IN = "not_in"
    
    def __init__(self, framework_path: str, max_workers: int = 1):
        """
        Initialize the SpecMapper.
        
        Args:
            framework_path: Path to the framework directory
            max_workers: Maximum parallel workers for processing
        """
        self.framework_path = framework_path
        self.max_workers = max_workers
        self._mapping_cache: Dict[str, Dict] = {}
        
        self.logger = pipeline_config.get_logger()
        self.validator = utility.JSONValidator(
            os.path.join(self.framework_path, FrameworkPaths.SPEC_MAPPING_SCHEMA_PATH)
        )
    
    def apply_mappings(
        self,
        specs: Dict,
        global_version: Optional[str] = None,
        ignore_errors: bool = False
    ) -> Dict:
        """
        Apply version mappings to specs using parallel processing.
        
        Args:
            specs: Dictionary of spec_path -> spec_payload
            global_version: Global mapping version to apply
            ignore_errors: If True, continue processing on errors
            
        Returns:
            Dictionary of processed specs
        """
        self.logger.info(
            "Spec Mapper - Applying Mappings:\n"
            f"    Max Workers: {self.max_workers}\n"
            f"    Global Dataflow Spec Version (optional): {global_version}"
            f"    Spec Count: {len(specs) if specs else 0}"
        )

        if not specs:
            return specs
        
        # Process specs in parallel
        results = {}
        errors = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_path = {
                executor.submit(
                    self._apply_mapping_to_spec,
                    spec_path,
                    spec_payload,
                    global_version
                ): spec_path
                for spec_path, spec_payload in specs.items()
            }
            
            for future in as_completed(future_to_path):
                spec_path, spec_payload, error = future.result()
                if error:
                    errors[spec_path] = error
                    self.logger.warning(f"Failed to apply mapping for {spec_path}: {error}")
                results[spec_path] = spec_payload
        
        if errors and not ignore_errors:
            self.logger.warning(f"Some specs failed during mapping: {errors}")
        
        return results
    
    def get_mapping(self, version: str) -> Dict:
        """
        Load, validate, and cache mapping configuration for a version.
        
        Args:
            version: Version string (e.g., "0.2.0")
            
        Returns:
            Mapping configuration dictionary
        """
        if version in self._mapping_cache:
            return self._mapping_cache[version]
        
        mapping_path = os.path.join(
            self.framework_path,
            FrameworkPaths.DATAFLOW_SPEC_MAPPING_PATH,
            version,
            "dataflow_spec_mapping.json"
        )
        
        try:
            mapping = utility.get_json_from_file(mapping_path, True)
            
            errors = self.validator.validate(mapping)
            if errors:
                raise ValueError(f"Spec mapping validation failed for {mapping_path}: {errors}")
            
            self._mapping_cache[version] = mapping
            return mapping
        except Exception as e:
            msg = f"Error loading spec mapping version {version}: {str(e)}"
            self.logger.error(msg)
            raise FileNotFoundError(msg) from e
    
    def _apply_mapping_to_spec(
        self,
        spec_path: str,
        spec_payload: Dict,
        global_version: Optional[str]
    ) -> Tuple[str, Dict, Optional[str]]:
        """
        Apply mapping to a single spec.
        
        Returns:
            Tuple of (spec_path, updated_payload, error_message)
        """
        try:
            spec_id = spec_payload.get(self.Keys.DATA_FLOW_ID, "").strip().lower()
            spec_type = spec_payload.get(self.Keys.DATA_FLOW_TYPE, "").strip().lower()
            spec_data = spec_payload.get(self.Keys.DATA)
            
            # Get mapping configuration
            mapping = {}
            if global_version:
                mapping = self.get_mapping(global_version)
            
            # Check for spec-specific version override
            spec_version = spec_data.get(self.Keys.DATA_FLOW_VERSION)
            if spec_version:
                mapping = self.get_mapping(spec_version)
                self.logger.info(
                    f"Using spec-specific mapping version {spec_version} for {spec_id}"
                )
            
            if not mapping:
                return spec_path, spec_payload, None
            
            # Merge global and spec-type specific mappings
            global_mappings = mapping.get(self.Keys.GLOBAL, {})
            spec_type_mappings = mapping.get(spec_type, {})
            key_mappings = {**global_mappings, **spec_type_mappings}
            
            if key_mappings:
                spec_data = self._apply_operations(spec_data, key_mappings, spec_path)
                spec_payload[self.Keys.DATA] = spec_data
            
            return spec_path, spec_payload, None
            
        except Exception as e:
            return spec_path, spec_payload, str(e)
    
    def _apply_operations(
        self,
        spec_data: Dict,
        mappings: Dict,
        spec_path: str
    ) -> Dict:
        """
        Apply all mapping operations to spec data.
        
        Operations are applied in order:
        1. move - Copy values to new locations
        2. rename_specific - Rename specific key paths
        3. rename_all - Recursively rename keys
        4. delete - Remove keys (including moved source keys)
        """
        rename_all_ops = mappings.get("rename_all", {})
        rename_specific_ops = mappings.get("rename_specific", {})
        move_ops = mappings.get("move", {})
        delete_ops = mappings.get("delete", {})
        
        moved_keys = []
        
        self.logger.debug(f"Applying mapping to spec: {spec_path}")
        
        # 1. Move operations (recursive)
        if move_ops:
            self.logger.debug(f"Applying move operations: {move_ops}")
            for src, dest_config in move_ops.items():
                # Parse the destination and condition from config
                if isinstance(dest_config, str):
                    dest = dest_config
                    condition = None
                elif isinstance(dest_config, dict):
                    dest = dest_config.get("to")
                    condition = dest_config.get("condition")
                else:
                    continue
                
                if dest:
                    # Apply move recursively throughout the spec
                    spec_data = self._move_key_recursive(spec_data, src, dest, condition)
                    moved_keys.append(src)
        
        # 2. Rename specific operations
        if rename_specific_ops:
            self.logger.debug(f"Applying rename specific operations: {rename_specific_ops}")
            for src, dest_config in rename_specific_ops.items():
                dest, should_apply = self._parse_conditional_operation(dest_config, spec_data)
                if should_apply and dest:
                    self._rename_key_specific(spec_data, src, dest)
                elif not should_apply:
                    self.logger.debug(f"Skipping rename '{src}' - condition not met")
        
        # 3. Rename all operations (recursive)
        if rename_all_ops:
            self.logger.debug(f"Applying rename all operations: {rename_all_ops}")
            filtered_rename_all = {}
            for src, dest_config in rename_all_ops.items():
                dest, should_apply = self._parse_conditional_operation(dest_config, spec_data)
                if should_apply and dest:
                    filtered_rename_all[src] = dest
            if filtered_rename_all:
                spec_data = self._rename_keys_recursive(spec_data, filtered_rename_all)
        
        # 4. Delete moved source keys (already handled by _move_key_recursive)
        # The recursive move operation removes the source key as part of the move
        
        # 5. Delete explicit keys
        if delete_ops:
            self.logger.debug(f"Applying delete operations: {delete_ops}")
            for key, delete_config in delete_ops.items():
                if isinstance(delete_config, bool) and delete_config:
                    self._delete_key(spec_data, key)
                elif isinstance(delete_config, dict):
                    _, should_apply = self._parse_conditional_operation(delete_config, spec_data)
                    if should_apply:
                        self._delete_key(spec_data, key)
                else:
                    self._delete_key(spec_data, key)
        
        self.logger.info(f"Mapping applied to spec: {spec_path}")
        self.logger.info(f"Mapped spec: {spec_data}")
        return spec_data

    # Condition Evaluation
    def _parse_conditional_operation(
        self,
        operation_value: Any,
        data: Dict
    ) -> Tuple[Optional[str], bool]:
        """
        Parse an operation value that may be simple or conditional.
        
        Simple format: "targetDetails.newKey"
        Conditional format: {"to": "...", "condition": {...}}
        
        Returns:
            Tuple of (target_value, should_apply)
        """
        if isinstance(operation_value, str):
            return operation_value, True
        elif isinstance(operation_value, dict):
            target = operation_value.get("to")
            condition = operation_value.get("condition")
            should_apply = self._evaluate_condition(data, condition)
            return target, should_apply
        else:
            self.logger.warning(f"Invalid operation value format: {operation_value}")
            return None, False
    
    def _evaluate_condition(self, data: Dict, condition: Optional[Dict]) -> bool:
        """
        Evaluate a condition against spec data.
        
        Condition format:
        {
            "key": "sourceType",              # dot notation path
            "operator": "not_equal_to",       # equal_to, not_equal_to, in, not_in
            "value": "python"                 # comparison value
        }
        """
        if not condition:
            return True
        
        key_path = condition.get("key", "")
        operator = condition.get("operator", self.Operators.EQUAL_TO)
        expected_value = condition.get("value")
        
        actual_value = self._get_nested_value(data, key_path)
        
        if operator == self.Operators.EQUAL_TO:
            return actual_value == expected_value
        elif operator == self.Operators.NOT_EQUAL_TO:
            return actual_value != expected_value
        elif operator == self.Operators.IN:
            if not isinstance(expected_value, list):
                raise ValueError(f"Spec mapping error: Invalid expected value type: {type(expected_value)} specified in condition: {condition}. Expected list.")
            return actual_value in expected_value
        elif operator == self.Operators.NOT_IN:
            if not isinstance(expected_value, list):
                raise ValueError(f"Spec mapping error: Invalid expected value type: {type(expected_value)} specified in condition: {condition}. Expected list.")
            return actual_value not in expected_value
        else:
            raise ValueError(f"Spec mapping error: Unknown condition operator: {operator} specified in condition: {condition}.")
    
    # Key Operations
    @staticmethod
    def _get_nested_value(data: Dict, key_path: str) -> Any:
        """Get a value from a nested dict using dot notation."""
        parts = key_path.split(".")
        current = data
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current
    
    @staticmethod
    def _get_parent_and_key(data: Dict, path: list, create_missing: bool = True) -> Tuple[Optional[Dict], str]:
        """
        Return the parent dict and final key name for a path.
        
        Args:
            data: The dictionary to traverse
            path: List of keys representing the path
            create_missing: If True, create intermediate dicts. If False, return None for parent if path doesn't exist.
        
        Returns:
            Tuple of (parent_dict, final_key). parent_dict is None if create_missing=False and path doesn't exist.
        """
        current = data
        for k in path[:-1]:
            if create_missing:
                current = current.setdefault(k, {})
            else:
                if not isinstance(current, dict) or k not in current:
                    return None, path[-1]
                current = current[k]
        return current, path[-1]

    def _move_key_recursive(
        self,
        obj: Any,
        src_path: str,
        dest_path: str,
        condition: Optional[Dict],
        context: Optional[Dict] = None
    ) -> Any:
        """
        Recursively move keys throughout the spec structure.
        
        For a src_path like "sourceDetails.pythonFunctionPath" and dest_path 
        "sourceDetails.pythonTransform.functionPath", this will find ALL occurrences
        of sourceDetails containing pythonFunctionPath and move them.
        
        The condition is evaluated against the parent context (e.g., the object 
        containing sourceDetails, which also has sourceType).
        """
        if isinstance(obj, dict):
            src_parts = src_path.split(".")
            dest_parts = dest_path.split(".")
            result = {}
            
            for key, value in obj.items():
                # Check if this is a match: key starts path, value is dict with source key, condition met
                if (key == src_parts[0] and 
                    isinstance(value, dict) and 
                    len(src_parts) == 2 and 
                    src_parts[1] in value and
                    self._evaluate_condition(obj, condition)):
                    
                    # Transform: remove source key and create nested destination
                    new_value = {k: v for k, v in value.items() if k != src_parts[1]}
                    current = new_value
                    for dest_key in dest_parts[1:-1]:
                        current = current.setdefault(dest_key, {})
                    current[dest_parts[-1]] = value[src_parts[1]]
                    
                    result[key] = self._move_key_recursive(new_value, src_path, dest_path, condition, obj)
                else:
                    result[key] = self._move_key_recursive(value, src_path, dest_path, condition, obj)
            
            return result
        
        if isinstance(obj, list):
            return [self._move_key_recursive(item, src_path, dest_path, condition, context) for item in obj]
        
        return obj
    
    def _move_key(self, data: Dict, src_path: str, dest_path: str) -> None:
        """Move a key and its value from src_path to dest_path (non-recursive, for root-level moves)."""
        src_parts = src_path.split(".")
        dest_parts = dest_path.split(".")
        
        # Check source exists WITHOUT creating intermediate dicts
        src_parent, src_key = self._get_parent_and_key(data, src_parts, create_missing=False)
        if src_parent is None or src_key not in src_parent:
            return
        
        value = src_parent[src_key]
        # Create destination path (this is intentional)
        dest_parent, dest_key = self._get_parent_and_key(data, dest_parts, create_missing=True)
        dest_parent[dest_key] = value
    
    def _rename_key_specific(self, data: Dict, current_key: str, new_key: str) -> None:
        """Rename a specific key at an exact path."""
        current_parts = current_key.split(".")
        # Check source exists WITHOUT creating intermediate dicts
        parent, key = self._get_parent_and_key(data, current_parts, create_missing=False)
        if parent is None or key not in parent:
            return
        
        new_key_name = new_key.split(".")[-1]
        parent[new_key_name] = parent.pop(key)
    
    def _rename_keys_recursive(self, obj: Any, key_mapping: Dict) -> Any:
        """Recursively rename keys in nested dictionaries."""
        if isinstance(obj, dict):
            renamed_obj = {}
            for key, value in obj.items():
                new_key = key_mapping.get(key, key)
                if new_key != key:
                    self.logger.debug(f"Renaming key '{key}' to '{new_key}'")
                renamed_obj[new_key] = self._rename_keys_recursive(value, key_mapping)
            return renamed_obj
        elif isinstance(obj, list):
            return [self._rename_keys_recursive(item, key_mapping) for item in obj]
        else:
            return obj
    
    def _delete_key(self, data: Dict, src_path: str) -> None:
        """Delete a key and its value from a nested dict."""
        src_parts = src_path.split(".")
        # Check source exists WITHOUT creating intermediate dicts
        src_parent, src_key = self._get_parent_and_key(data, src_parts, create_missing=False)
        if src_parent is not None and src_key in src_parent:
            src_parent.pop(src_key)

