#!/usr/bin/env python3
"""
Validate dataflow JSON files against their schemas.

This script recursively searches for dataflow specification files (*_main.json)
and validates them against the project's JSON schemas.

Usage:
    python scripts/validate_dataflows.py                           # Validate all dataflow files (with version mapping)
    python scripts/validate_dataflows.py samples/bronze_sample/    # Validate all files in specific directory
    python scripts/validate_dataflows.py path/to/file_main.json   # Validate specific file
    python scripts/validate_dataflows.py --no-mapping              # Validate without applying version mappings
    
Examples:
    # From project root
    python scripts/validate_dataflows.py
    
    # Validate only bronze samples
    python scripts/validate_dataflows.py samples/bronze_sample/
    
    # Validate without version mapping (strict validation against current schema)
    python scripts/validate_dataflows.py --no-mapping samples/bronze_sample/
    
    # Validate a single file
    python scripts/validate_dataflows.py samples/bronze_sample/src/dataflows/base_samples/dataflowspec/customer_main.json
"""

import argparse
import json
import sys
import os
from pathlib import Path
from typing import List, Tuple, Optional, Dict
import warnings
import copy

# Suppress deprecation warnings from jsonschema
warnings.filterwarnings('ignore', category=DeprecationWarning)

try:
    import jsonschema
    from jsonschema import RefResolver, Draft7Validator
except ImportError:
    print("Error: jsonschema package not found. Install it with: pip install jsonschema")
    sys.exit(1)

# ANSI color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def find_project_root() -> Path:
    """Find the project root directory (contains src/schemas/)."""
    # Start from the script location
    current = Path(__file__).parent.resolve()
    
    # Go up to find the project root
    while current != current.parent:
        if (current / "src" / "schemas" / "main.json").exists():
            return current
        current = current.parent
    
    raise FileNotFoundError("Could not find project root (looking for src/schemas/main.json)")


def find_dataflow_files(search_path: Path) -> List[Path]:
    """
    Find all dataflow *_main.json files recursively.
    
    Args:
        search_path: Directory or file path to search
        
    Returns:
        List of Path objects for dataflow files
    """
    if search_path.is_file():
        if search_path.name.endswith("_main.json"):
            return [search_path]
        else:
            return []
    
    return list(search_path.rglob("**/dataflows/**/dataflowspec/*_main.json"))


def load_dataflow_spec_mapping(project_root: Path, version: str) -> Optional[Dict]:
    """
    Load the dataflow spec mapping for a specific version.
    
    Args:
        project_root: Root directory of the project
        version: Version string (e.g., "0.1.0")
        
    Returns:
        Mapping dictionary or None if not found
    """
    mapping_path = project_root / "src" / "config" / "dataflow_spec_mapping" / version / "dataflow_spec_mapping.json"
    
    if not mapping_path.exists():
        return None
    
    try:
        with open(mapping_path) as f:
            return json.load(f)
    except Exception as e:
        print(f"{YELLOW}Warning: Could not load mapping for version {version}: {e}{RESET}")
        return None


def apply_rename_all(data: Dict, rename_map: Dict) -> None:
    """
    Recursively rename all occurrences of keys in the data structure.
    
    Args:
        data: Dictionary to modify in-place
        rename_map: Map of old_key -> new_key
    """
    if not isinstance(data, dict):
        return
    
    # Create list of keys to avoid modifying dict during iteration
    keys_to_rename = []
    for old_key in list(data.keys()):
        if old_key in rename_map:
            keys_to_rename.append((old_key, rename_map[old_key]))
    
    # Perform renames
    for old_key, new_key in keys_to_rename:
        data[new_key] = data.pop(old_key)
    
    # Recursively process nested structures
    for value in data.values():
        if isinstance(value, dict):
            apply_rename_all(value, rename_map)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    apply_rename_all(item, rename_map)


def apply_rename_specific(data: Dict, rename_map: Dict) -> None:
    """
    Rename specific keys at specific paths (e.g., "targetDetails.topic" -> "targetDetails.name").
    
    Args:
        data: Dictionary to modify in-place
        rename_map: Map of path -> new_key_name
    """
    for old_path, new_key in rename_map.items():
        path_parts = old_path.split('.')
        
        # Navigate to parent
        current = data
        for part in path_parts[:-1]:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                break
        else:
            # Rename the final key
            old_key = path_parts[-1]
            if isinstance(current, dict) and old_key in current:
                current[new_key] = current.pop(old_key)


def apply_move(data: Dict, move_map: Dict) -> None:
    """
    Move values from one path to another (e.g., "targetDetails.topic" -> "targetDetails.kafkaOptions.topic").
    
    Args:
        data: Dictionary to modify in-place
        move_map: Map of source_path -> destination_path
    """
    for src_path, dest_path in move_map.items():
        src_parts = src_path.split('.')
        dest_parts = dest_path.split('.')
        
        # Get source value
        current = data
        for part in src_parts[:-1]:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                break
        else:
            src_key = src_parts[-1]
            if isinstance(current, dict) and src_key in current:
                value = current[src_key]
                
                # Navigate/create destination path
                dest_current = data
                for part in dest_parts[:-1]:
                    if part not in dest_current:
                        dest_current[part] = {}
                    dest_current = dest_current[part]
                
                # Set at destination
                dest_key = dest_parts[-1]
                dest_current[dest_key] = value
                
                # Remove from source
                del current[src_key]


def apply_dataflow_spec_mapping(data: Dict, mapping: Dict) -> Dict:
    """
    Apply dataflow spec mapping transformations to the data.
    
    Args:
        data: Dataflow spec dictionary
        mapping: Mapping configuration
        
    Returns:
        Transformed dataflow spec (a deep copy)
    """
    # Work on a copy to avoid modifying the original
    transformed = copy.deepcopy(data)
    
    # Get global mappings
    global_mapping = mapping.get("global", {})
    
    # Get spec-type specific mappings
    spec_type = data.get("dataFlowType", "").lower()
    type_mapping = mapping.get(spec_type, {})
    
    # Combine mappings (type-specific overrides global)
    combined_mapping = {**global_mapping, **type_mapping}
    
    # Apply transformations in order
    if "rename_all" in combined_mapping:
        apply_rename_all(transformed, combined_mapping["rename_all"])
    
    if "rename_specific" in combined_mapping:
        apply_rename_specific(transformed, combined_mapping["rename_specific"])
    
    if "move" in combined_mapping:
        apply_move(transformed, combined_mapping["move"])
    
    return transformed


def validate_file(file_path: Path, schema_path: Path, apply_mapping: bool = False, 
                  project_root: Optional[Path] = None) -> Tuple[bool, List[str], Optional[str]]:
    """
    Validate a single JSON file against the schema.
    
    Args:
        file_path: Path to the JSON file to validate
        schema_path: Path to the schema file
        apply_mapping: Whether to apply version mapping before validation
        project_root: Root directory of the project (required if apply_mapping is True)
        
    Returns:
        Tuple of (is_valid, error_messages_list, version_applied)
    """
    version_applied = None
    
    try:
        with open(file_path) as f:
            data = json.load(f)
        
        # Apply version mapping if requested
        if apply_mapping and project_root:
            version = data.get("dataFlowVersion")
            if version:
                mapping = load_dataflow_spec_mapping(project_root, version)
                if mapping:
                    data = apply_dataflow_spec_mapping(data, mapping)
                    version_applied = version
        
        with open(schema_path) as f:
            schema = json.load(f)
        
        # Create resolver for $ref references
        schema_dir = os.path.dirname(os.path.abspath(schema_path))
        resolver = RefResolver(base_uri=f'file://{schema_dir}/', referrer=schema)
        
        # Create validator and collect all errors
        validator = Draft7Validator(schema, resolver=resolver)
        errors = list(validator.iter_errors(data))
        
        if not errors:
            return True, ["Valid"], version_applied
        
        # Format all error messages
        error_messages = []
        for error in errors:
            error_msg = f"{error.message}"
            
            # Handle "is not valid under any of the given schemas" or "should not be valid under" (validation failure)
            if "is not valid under any of the given schemas" in error_msg or ("should not be valid under" in error_msg and "'datetimeFormat']}" in error_msg):
                # Check if this is a versionType/datetimeFormat issue
                try:
                    # Navigate to the error location
                    error_data = data
                    for path_part in error.path:
                        error_data = error_data[path_part]
                    
                    # Check if it's the historicalSnapshotFileSource anyOf issue
                    if isinstance(error_data, dict) and 'versionType' in error_data:
                        version_type = error_data.get('versionType')
                        has_datetime = 'datetimeFormat' in error_data
                        
                        if version_type == 'integer' and has_datetime:
                            error_msg = f"Property 'datetimeFormat' is not allowed when versionType is 'integer'"
                        elif version_type == 'timestamp' and not has_datetime:
                            error_msg = f"Property 'datetimeFormat' is required when versionType is 'timestamp'"
                except:
                    pass  # Fall back to original message
            
            # Handle "should not be valid under" errors (from not/anyOf constraints)
            elif "should not be valid under" in error_msg and "anyOf" in error_msg:
                # Extract which properties are disallowed from the schema
                try:
                    # The schema might have a 'not' wrapper containing the anyOf
                    anyof_schema = error.schema.get('not', {}).get('anyOf', [])
                    if not anyof_schema:
                        anyof_schema = error.schema.get('anyOf', [])
                    
                    if anyof_schema:
                        disallowed_props = []
                        for condition in anyof_schema:
                            if 'required' in condition:
                                disallowed_props.extend(condition['required'])
                        
                        # Check which of these properties are actually present in the data
                        present_props = []
                        for prop in disallowed_props:
                            if prop in data:
                                present_props.append(prop)
                        
                        if present_props:
                            props_str = ', '.join(f"'{p}'" for p in present_props)
                            error_msg = f"Properties {props_str} are not allowed in this context"
                        else:
                            error_msg = f"One or more disallowed properties are present"
                except:
                    pass  # Fall back to original message
            
            if error.path:
                path_str = '.'.join(str(p) for p in error.path)
                if "at path:" not in error_msg:  # Don't add path twice
                    error_msg += f" at path: {path_str}"
            
            error_messages.append(error_msg)
        
        return False, error_messages, version_applied
        
    except FileNotFoundError as e:
        return False, [f"File not found: {e}"], version_applied
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON: {e}"], version_applied
    except Exception as e:
        return False, [f"Error: {e}"], version_applied


def main():
    parser = argparse.ArgumentParser(
        description="Validate dataflow JSON files against schemas",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                 # Validate all dataflow files
  %(prog)s samples/bronze_sample/          # Validate specific directory
  %(prog)s path/to/customer_main.json      # Validate single file
        """
    )
    parser.add_argument(
        'path',
        nargs='?',
        default='.',
        help='Path to file or directory to validate (default: current directory, searches recursively)'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show verbose output'
    )
    parser.add_argument(
        '--no-mapping',
        action='store_true',
        help='Skip version mapping transformations (validate strict against current schema without transforming legacy properties)'
    )
    
    args = parser.parse_args()
    
    # Resolve search path
    search_path = Path(args.path).resolve()
    
    if not search_path.exists():
        print(f"{RED}Error: Path does not exist: {args.path}{RESET}")
        return 1
    
    # Find project root and schema
    try:
        project_root = find_project_root()
        schema_path = project_root / "src" / "schemas" / "main.json"
    except FileNotFoundError as e:
        print(f"{RED}Error: {e}{RESET}")
        return 1
    
    # Apply mapping by default unless --no-mapping is specified
    apply_mapping = not args.no_mapping
    
    if args.verbose:
        print(f"{BLUE}Project root: {project_root}{RESET}")
        print(f"{BLUE}Schema path: {schema_path}{RESET}")
        print(f"{BLUE}Search path: {search_path}{RESET}")
        print(f"{BLUE}Apply mapping: {apply_mapping}{RESET}\n")
    
    # Find files to validate
    files = find_dataflow_files(search_path)
    
    if not files:
        print(f"{YELLOW}No dataflow files found in: {args.path}{RESET}")
        return 0
    
    # Validate each file
    if args.no_mapping:
        mode_str = " (strict mode - no version mapping)"
    else:
        mode_str = " (with version mapping)"
    print(f"Validating {len(files)} file(s){mode_str}...\n")
    
    passed = 0
    failed = 0
    mapped_count = 0
    
    for file_path in sorted(files):
        # Display relative path from project root if possible
        try:
            rel_path = file_path.relative_to(project_root)
        except ValueError:
            rel_path = file_path
        
        is_valid, error_messages, version_applied = validate_file(
            file_path, schema_path, 
            apply_mapping=apply_mapping,
            project_root=project_root
        )
        
        if is_valid:
            version_str = f" {BLUE}[v{version_applied}]{RESET}" if version_applied else ""
            print(f"{GREEN}✓{RESET} {rel_path}{version_str}")
            passed += 1
            if version_applied:
                mapped_count += 1
        else:
            version_str = f" {BLUE}[v{version_applied}]{RESET}" if version_applied else ""
            error_count = len(error_messages)
            error_label = "error" if error_count == 1 else "errors"
            print(f"{RED}✗{RESET} {rel_path}{version_str} {RED}({error_count} {error_label}){RESET}")
            for i, message in enumerate(error_messages, 1):
                print(f"  {RED}{i}. {message}{RESET}")
            failed += 1
    
    # Summary
    print(f"\n{'='*60}")
    print(f"Total: {len(files)} | {GREEN}Passed: {passed}{RESET} | {RED}Failed: {failed}{RESET}")
    if apply_mapping and mapped_count > 0:
        print(f"Mapped: {BLUE}{mapped_count}{RESET} files had version mappings applied")
    
    return 1 if failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())

